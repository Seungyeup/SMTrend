from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import requests


def execute_statement(
    *,
    trino_statement_url: str,
    sql: str,
    user: str,
    catalog: str,
    schema: str,
) -> dict[str, Any]:
    headers = {
        "X-Trino-User": user,
        "X-Trino-Catalog": catalog,
        "X-Trino-Schema": schema,
    }
    response = requests.post(trino_statement_url, data=sql, headers=headers, timeout=60)
    response.raise_for_status()
    payload = response.json()

    if "error" in payload:
        raise RuntimeError(payload["error"]["message"])

    columns = payload.get("columns", [])
    data = payload.get("data", [])
    next_uri = payload.get("nextUri")
    while next_uri:
        poll = requests.get(next_uri, headers={"X-Trino-User": user}, timeout=60)
        poll.raise_for_status()
        payload = poll.json()
        if "error" in payload:
            raise RuntimeError(payload["error"]["message"])
        if not columns:
            columns = payload.get("columns", columns)
        data.extend(payload.get("data", []))
        next_uri = payload.get("nextUri")

    return {
        "columns": columns,
        "data": data,
    }


def split_sql(sql_text: str) -> list[str]:
    statements = []
    chunks = sql_text.split(";")
    for chunk in chunks:
        stmt = chunk.strip()
        if stmt:
            statements.append(stmt)
    return statements


def execute_sql_text(
    *,
    trino_statement_url: str,
    sql_text: str,
    user: str,
    catalog: str,
    schema: str,
) -> list[dict[str, Any]]:
    statements = split_sql(sql_text)
    results: list[dict[str, Any]] = []
    for statement in statements:
        results.append(
            execute_statement(
                trino_statement_url=trino_statement_url,
                sql=statement,
                user=user,
                catalog=catalog,
                schema=schema,
            )
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SQL file through Trino HTTP API")
    sql_group = parser.add_mutually_exclusive_group(required=True)
    sql_group.add_argument("--sql-file")
    sql_group.add_argument("--sql")
    parser.add_argument(
        "--trino-statement-url",
        default=os.getenv("TRINO_STATEMENT_URL", "http://localhost:8080/v1/statement"),
    )
    parser.add_argument("--user", default="airflow")
    parser.add_argument("--catalog", default="hive")
    parser.add_argument("--schema", default="market")
    parser.add_argument("--print-rows", action="store_true")
    args = parser.parse_args()

    sql_text = args.sql or Path(args.sql_file).read_text(encoding="utf-8")
    results = execute_sql_text(
        trino_statement_url=args.trino_statement_url,
        sql_text=sql_text,
        user=args.user,
        catalog=args.catalog,
        schema=args.schema,
    )

    if args.print_rows:
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
