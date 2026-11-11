import os
from fastapi import FastAPI

app = FastAPI()
VERSION = os.environ.get("APP_VERSION", "1.0.0")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/version")
def version():
    return {"version": VERSION}

@app.post("/predict")
def predict(payload: dict):
    return {"prediction": "setosa", "input": payload}
