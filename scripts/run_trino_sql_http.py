from __future__ import annotations

import argparse
from pathlib import Path

import requests


def execute_statement(
    *,
    trino_statement_url: str,
    sql: str,
    user: str,
    catalog: str,
    schema: str,
) -> None:
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

    next_uri = payload.get("nextUri")
    while next_uri:
        poll = requests.get(next_uri, headers={"X-Trino-User": user}, timeout=60)
        poll.raise_for_status()
        payload = poll.json()
        if "error" in payload:
            raise RuntimeError(payload["error"]["message"])
        next_uri = payload.get("nextUri")


def split_sql(sql_text: str) -> list[str]:
    statements = []
    chunks = sql_text.split(";")
    for chunk in chunks:
        stmt = chunk.strip()
        if stmt:
            statements.append(stmt + ";")
    return statements


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SQL file through Trino HTTP API")
    parser.add_argument("--sql-file", required=True)
    parser.add_argument("--trino-statement-url", default="http://trino:8080/v1/statement")
    parser.add_argument("--user", default="airflow")
    parser.add_argument("--catalog", default="hive")
    parser.add_argument("--schema", default="market")
    args = parser.parse_args()

    sql_text = Path(args.sql_file).read_text(encoding="utf-8")
    statements = split_sql(sql_text)
    for statement in statements:
        execute_statement(
            trino_statement_url=args.trino_statement_url,
            sql=statement,
            user=args.user,
            catalog=args.catalog,
            schema=args.schema,
        )


if __name__ == "__main__":
    main()
