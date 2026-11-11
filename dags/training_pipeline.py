from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import logging, subprocess

default_args = {"retries": 2, "retry_delay": timedelta(seconds=30)}
QUALITY_THRESHOLD = 0.6
PROJECT_DIR = "/home/hannan/Desktop/mlops_A3"


def validate_dataset(**_):
    import pandas as pd
    df = pd.read_csv(f"{PROJECT_DIR}/data/iris.csv")
    if df.empty:
        raise ValueError("Dataset is empty")
    logging.info(f"Validated {len(df)} rows")


def preprocess_data(**_):
    logging.info("Preprocessing ok")


def train_model(**_):
    subprocess.run(["python", "training/train.py", "100"], check=True, cwd=PROJECT_DIR)


def evaluate_and_log_mlflow(**kwargs):
    import mlflow
    c = mlflow.tracking.MlflowClient(tracking_uri="http://localhost:5000")
    exp = c.get_experiment_by_name("iris-training")
    runs = c.search_runs([exp.experiment_id], order_by=["metrics.f1_score DESC"], max_results=1)
    f1 = runs[0].data.metrics["f1_score"]
    kwargs["ti"].xcom_push(key="f1", value=f1)
    logging.info(f"best f1={f1}")


def quality_gate(**kwargs):
    f1 = kwargs["ti"].xcom_pull(key="f1", task_ids="evaluate_and_log_mlflow")
    if f1 < QUALITY_THRESHOLD:
        raise ValueError(f"Quality gate failed: f1={f1} < {QUALITY_THRESHOLD}")
    logging.info("Quality gate passed")


with DAG(
    "training_pipeline",
    default_args=default_args,
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
) as dag:
    t1 = PythonOperator(task_id="validate_dataset", python_callable=validate_dataset)
    t2 = PythonOperator(task_id="preprocess_data", python_callable=preprocess_data)
    t3 = PythonOperator(task_id="train_model", python_callable=train_model)
    t4 = PythonOperator(task_id="evaluate_and_log_mlflow", python_callable=evaluate_and_log_mlflow)
    t5 = PythonOperator(task_id="quality_gate", python_callable=quality_gate)
    t1 >> t2 >> t3 >> t4 >> t5
