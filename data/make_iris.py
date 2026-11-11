# data/make_iris.py — run once
from sklearn.datasets import load_iris
d = load_iris(as_frame=True)
d.frame.to_csv("data/iris.csv", index=False)