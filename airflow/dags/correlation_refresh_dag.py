from datetime import datetime
import importlib

def _load_airflow_symbols():
    try:
        dag_cls = importlib.import_module("airflow").DAG
        bash_op_cls = importlib.import_module("airflow.operators.bash").BashOperator
        return dag_cls, bash_op_cls
    except ModuleNotFoundError:
        class DagFallback:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        class BashOperatorFallback:
            def __init__(self, *args, **kwargs):
                pass

            def __rshift__(self, other):
                return other

        return DagFallback, BashOperatorFallback


DAG, BashOperator = _load_airflow_symbols()


with DAG(
    dag_id="correlation_refresh_daily",
    start_date=datetime(2025, 1, 1),
    schedule="30 9 * * 1-5",
    catchup=False,
    tags=["gold", "correlation", "trino"],
) as dag:
    create_external = BashOperator(
        task_id="create_external_tables",
        bash_command=(
            "cd /opt/project && "
            "python scripts/run_trino_sql_http.py "
            "--sql-file /opt/project/trino/sql/01_create_external_tables.sql"
        ),
    )

    refresh_gold = BashOperator(
        task_id="refresh_gold_tables",
        bash_command=(
            "cd /opt/project && "
            "python scripts/run_trino_sql_http.py "
            "--sql-file /opt/project/trino/sql/02_build_gold_tables.sql"
        ),
    )

    create_external >> refresh_gold
