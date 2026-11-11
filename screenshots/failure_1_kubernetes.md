# Failure Injection 1: Kubernetes bad image tag

## Injection
```
kubectl set image deployment/iris-api iris-api=iris-api:bad -n mlops-agent
```

## Resulting pod state
```
NAME                        READY   STATUS         RESTARTS   AGE
iris-api-644d56d745-4kh6c   1/1     Running        0          125m
iris-api-644d56d745-k4tr2   1/1     Running        0          125m
iris-api-d6b8944c9-5pnzc    0/1     ErrImagePull   0          5s
```

## Question asked to agent
"Why is my prediction API unavailable?"

## Agent's diagnosis
Correctly identified that 2/3 pods were healthy and serving traffic, and the
new pod (iris-api-d6b8944c9-5pnzc) was stuck in image-pull failure. Recommended
checking pod events and image reference rather than guessing at the cause.
(Full response saved in architecture.md / report.)

## Root cause
Deployment was updated to reference a non-existent image tag (iris-api:bad).

## Resolution
```
kubectl rollout undo deployment/iris-api -n mlops-agent
```
