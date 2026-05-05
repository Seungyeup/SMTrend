from __future__ import annotations

import json
import os

from superset.app import create_app


def _table_chart_params(dataset_id: int) -> str:
    params = {
        "datasource": f"{dataset_id}__table",
        "viz_type": "table",
        "query_mode": "raw",
        "all_columns": [
            "bucket_1m_utc",
            "symbol",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
            "tick_count",
        ],
        "order_by_cols": ["[\"bucket_1m_utc\", false]"],
        "adhoc_filters": [],
        "row_limit": 50,
        "order_desc": True,
    }
    return json.dumps(params)


def _timeseries_chart_params(dataset_id: int, time_range: str, time_column: str) -> str:
    params = {
        "datasource": f"{dataset_id}__table",
        "viz_type": "echarts_timeseries_line",
        "query_mode": "aggregate",
        "groupby": ["symbol"],
        "metrics": [
            {
                "expressionType": "SIMPLE",
                "column": {"column_name": "close_price"},
                "aggregate": "MAX",
                "label": "close_price",
            }
        ],
        "orderby": [["close_price", False]],
        "adhoc_filters": [],
        "row_limit": 1000,
        "granularity_sqla": time_column,
        "time_range": time_range,
        "x_axis": time_column,
    }
    return json.dumps(params)


def _dashboard_json_metadata(current_json: str | None, refresh_seconds: int) -> str:
    metadata: dict[str, object]
    if current_json:
        try:
            metadata = json.loads(current_json)
        except json.JSONDecodeError:
            metadata = {}
    else:
        metadata = {}
    metadata["refresh_frequency"] = refresh_seconds
    return json.dumps(metadata)


def _default_time_column(dataset_table: str) -> str:
    if dataset_table == "market_bar_1m":
        return "bucket_1m_utc"
    return "__time"


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _build_virtual_sql(*, schema: str | None, physical_table: str) -> str:
    if schema:
        return f'SELECT * FROM "{schema}"."{physical_table}"'
    return f'SELECT * FROM "{physical_table}"'


def main() -> None:
    app = create_app()
    with app.app_context():
        from superset.connectors.sqla.models import SqlaTable
        from superset.extensions import db
        from superset.models.core import Database
        from superset.models.dashboard import Dashboard
        from superset.models.slice import Slice

        session = db.session

        db_name = os.getenv("SUPERSET_DB_NAME", "Trino Market")
        db_uri = os.getenv("SUPERSET_DB_URI", "trino://trino@host.docker.internal:8080/hive/market")
        dataset_schema = _normalize_optional(os.getenv("SUPERSET_DATASET_SCHEMA", "market"))
        dataset_catalog = _normalize_optional(os.getenv("SUPERSET_DATASET_CATALOG", "hive"))
        dataset_table = os.getenv("SUPERSET_DATASET_TABLE", "market_bar_1m_trino")
        physical_table = os.getenv("SUPERSET_PHYSICAL_TABLE", "market_bar_1m")
        dashboard_title = os.getenv("SUPERSET_DASHBOARD_TITLE", "SMTrend Monitoring")
        table_chart_name = os.getenv("SUPERSET_TABLE_CHART_NAME", "Market bars by symbol")
        timeseries_chart_name = os.getenv("SUPERSET_TIMESERIES_CHART_NAME", "1-minute close price over time")
        timeseries_time_range = os.getenv("SUPERSET_TIMESERIES_TIME_RANGE", "Last 1 hour")
        dashboard_refresh_seconds = int(os.getenv("SUPERSET_DASHBOARD_REFRESH_SECONDS", "10"))
        time_column = os.getenv("SUPERSET_TIME_COLUMN", _default_time_column(dataset_table))

        database = session.query(Database).filter_by(database_name=db_name).one_or_none()
        if database is None:
            database = Database(database_name=db_name, sqlalchemy_uri=db_uri, expose_in_sqllab=True)
            session.add(database)
        else:
            database.sqlalchemy_uri = db_uri
            database.expose_in_sqllab = True
        session.commit()

        dataset = (
            session.query(SqlaTable)
            .filter_by(table_name=dataset_table)
            .one_or_none()
        )
        if dataset is None:
            dataset = SqlaTable(
                table_name=dataset_table,
                schema=dataset_schema,
                catalog=dataset_catalog,
                database_id=database.id,
                sql=_build_virtual_sql(schema=dataset_schema, physical_table=physical_table),
                is_sqllab_view=True,
            )
            session.add(dataset)
        else:
            dataset.schema = dataset_schema
            dataset.catalog = dataset_catalog
            dataset.database_id = database.id
            dataset.sql = _build_virtual_sql(schema=dataset_schema, physical_table=physical_table)
            dataset.is_sqllab_view = True
        session.commit()

        dataset.fetch_metadata()
        session.commit()

        dataset = (
            session.query(SqlaTable)
            .filter_by(table_name=dataset_table)
            .one()
        )

        table_chart = session.query(Slice).filter_by(slice_name=table_chart_name).one_or_none()
        if table_chart is None:
            table_chart = Slice(
                slice_name=table_chart_name,
                viz_type="table",
                datasource_type="table",
                datasource_id=dataset.id,
                params=_table_chart_params(dataset.id),
            )
            session.add(table_chart)
        else:
            table_chart.viz_type = "table"
            table_chart.datasource_type = "table"
            table_chart.datasource_id = dataset.id
            table_chart.params = _table_chart_params(dataset.id)

        timeseries_chart = session.query(Slice).filter_by(slice_name=timeseries_chart_name).one_or_none()
        if timeseries_chart is None:
            timeseries_chart = Slice(
                slice_name=timeseries_chart_name,
                viz_type="echarts_timeseries_line",
                datasource_type="table",
                datasource_id=dataset.id,
                params=_timeseries_chart_params(dataset.id, timeseries_time_range, time_column),
                cache_timeout=0,
            )
            session.add(timeseries_chart)
        else:
            timeseries_chart.viz_type = "echarts_timeseries_line"
            timeseries_chart.datasource_type = "table"
            timeseries_chart.datasource_id = dataset.id
            timeseries_chart.params = _timeseries_chart_params(dataset.id, timeseries_time_range, time_column)
            timeseries_chart.cache_timeout = 0
        session.commit()

        dashboard = session.query(Dashboard).filter_by(dashboard_title=dashboard_title).one_or_none()
        if dashboard is None:
            dashboard = Dashboard(dashboard_title=dashboard_title)
            session.add(dashboard)
            session.commit()

        if table_chart not in dashboard.slices:
            dashboard.slices.append(table_chart)
        if timeseries_chart not in dashboard.slices:
            dashboard.slices.append(timeseries_chart)
        dashboard.json_metadata = _dashboard_json_metadata(
            current_json=dashboard.json_metadata,
            refresh_seconds=dashboard_refresh_seconds,
        )

        session.commit()
        print(
            f"Bootstrapped Superset content: dashboard='{dashboard_title}', charts=['{table_chart_name}', '{timeseries_chart_name}'], dataset='{dataset_schema}.{dataset_table}', physical_table='{physical_table}', columns={len(dataset.columns)}"
        )


if __name__ == "__main__":
    main()
