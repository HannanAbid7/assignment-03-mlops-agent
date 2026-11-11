import subprocess, sys, mlflow
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score

def git_commit():
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()

def dvc_hash():
    try:
        for line in open("data/iris.csv.dvc"):
            if "md5" in line:
                return line.split("md5:")[1].strip()
    except FileNotFoundError:
        pass
    return "unknown"

def main(n_estimators=100, max_depth=None):
    mlflow.set_tracking_uri("http://localhost:5000")
    mlflow.set_experiment("iris-training")
    df = pd.read_csv("data/iris.csv")
    X, y = df.drop(columns=["target"]), df["target"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    with mlflow.start_run():
        model = RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42)
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        acc = accuracy_score(y_test, preds)
        f1 = f1_score(y_test, preds, average="macro")
        mlflow.log_param("n_estimators", n_estimators)
        mlflow.log_param("max_depth", max_depth)
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("f1_score", f1)
        mlflow.set_tag("git_commit", git_commit())
        mlflow.set_tag("dvc_data_hash", dvc_hash())
        mlflow.set_tag("dataset_version", "v1")
        mlflow.sklearn.log_model(model, "model")
        print(f"n_estimators={n_estimators} max_depth={max_depth} acc={acc:.3f} f1={f1:.3f}")

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    d = int(sys.argv[2]) if len(sys.argv) > 2 else None
    main(n, d)