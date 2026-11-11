# MLOps AI Agent

A conversational AI agent that inspects and operates a real MLOps stack
(DVC, MLflow, Apache Airflow, Kubernetes) through natural-language requests,
built for Assignment 03 (MLOps & Production AI Engineering).

The agent does not answer from its own training knowledge. Every operational
claim it makes (dataset versions, run metrics, pipeline status, pod health)
is backed by a real tool call against the running infrastructure.

## Architecture

See [architecture.md](architecture.md) for the full system design, tool
definitions, and permission model.

## Prerequisites

- Python 3.11+
- Docker
- `kind` (Kubernetes in Docker) and `kubectl`
- A Groq API key (or any OpenAI-compatible endpoint) for the LLM

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Create `.env` from `.env.example` and fill in:
```
LLM_API_KEY=<your key>
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-120b
AIRFLOW_ADMIN_PASSWORD=<see airflow_home/simple_auth_manager_passwords.json.generated after first start>
```

## Launching each service

**DVC** (dataset versioning — no server, just the CLI):
```bash
dvc init
dvc add data/iris.csv
dvc remote add -d localremote ../dvc_remote
dvc push
```

**MLflow** (experiment tracking server):
```bash
mlflow server --port 5000
python training/train.py 100   # logs a training run
```

**Kubernetes** (inference service):
```bash
docker build -t iris-api:1.0 .
kind create cluster
kind load docker-image iris-api:1.0
kubectl create namespace mlops-agent
kubectl apply -f kubernetes/ -n mlops-agent
```

**Airflow** (training pipeline orchestration):
```bash
pip install apache-airflow
export AIRFLOW_HOME=$(pwd)/airflow_home
airflow standalone
ln -sf $(pwd)/dags/training_pipeline.py $AIRFLOW_HOME/dags/training_pipeline.py
```
Airflow prints a generated admin password on first start, saved to
`airflow_home/simple_auth_manager_passwords.json.generated` — put that value
in `.env` as `AIRFLOW_ADMIN_PASSWORD`.

**The agent itself**:
```bash
uvicorn agent.main:app --port 9000
```

## Talking to the agent

```bash
curl -X POST localhost:9000/chat -H "Content-Type: application/json" \
  -d '{"message": "Find the best recent model, identify the dataset version used to train it, check the deployment status, and explain whether retraining is necessary."}'
```

## Running tests

```bash
pytest -v
```

All external services (MLflow, Airflow, Kubernetes) are mocked in the test
suite — no live infrastructure is required to run `pytest`.

## Project structure

```
agent/            orchestrator, FastAPI app, and the four tool modules
api/               the deployed FastAPI inference service (built into kubernetes/)
dags/              Airflow training pipeline DAG
data/              DVC-tracked dataset
kubernetes/        Deployment, Service, ConfigMap manifests
tests/             pytest suite (mocked tool tests)
screenshots/        evidence from failure injections and demo runs
.github/workflows/ CI pipeline (lint + tests on push/PR)
```

## Known limitations

See the "Known limitations and proposed improvements" section of the
technical report (`report.pdf` / `report.tex`).
