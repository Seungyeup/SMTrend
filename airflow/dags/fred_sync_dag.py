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

        return DagFallback, BashOperatorFallback


DAG, BashOperator = _load_airflow_symbols()


with DAG(
    dag_id="fred_daily_sync",
    start_date=datetime(2025, 1, 1),
    schedule="0 9 * * 1-5",
    catchup=False,
    tags=["macro", "fred", "batch"],
) as dag:
    sync_fred = BashOperator(
        task_id="sync_fred_macro",
        bash_command=(
            "cd /opt/project && "
            "python -m poc_ingestion.main fred-batch "
            "--series DFF,CPIAUCSL,UNRATE "
            "--limit 200 "
            "--bootstrap-servers ${KAFKA_BOOTSTRAP_SERVERS}"
        ),
    )

    sync_fred
