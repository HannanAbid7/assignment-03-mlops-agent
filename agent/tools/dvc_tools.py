import subprocess, hashlib
from pathlib import Path

ALLOWED = {"status", "list", "diff", "checkout"}

def _run_dvc(args):
    if args[0] not in ALLOWED:
        raise PermissionError(f"'{args[0]}' not allowed")
    r = subprocess.run(["dvc", *args], capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return r.stdout

def _run_git(args):
    r = subprocess.run(["git", *args], capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return r.stdout.strip()

def list_tracked_datasets(repo_path: str = "."):
    """List all DVC-tracked dataset files in the repo."""
    return [str(p) for p in Path(repo_path).rglob("*.dvc")]

def get_current_version(dataset_dvc_file: str = "data/iris.csv.dvc"):
    """Return the current DVC md5 hash and git commit for a dataset."""
    content = Path(dataset_dvc_file).read_text()
    md5 = next((l.split("md5:")[1].strip() for l in content.splitlines() if "md5:" in l), None)
    return {"dataset": dataset_dvc_file, "md5": md5, "git_commit": _run_git(["rev-parse", "HEAD"])}

def compare_versions(commit_a: str, commit_b: str, dataset_dvc_file: str = "data/iris.csv.dvc"):
    """Compare a dataset's recorded hash between two git commits/tags."""
    a = _run_git(["show", f"{commit_a}:{dataset_dvc_file}"])
    b = _run_git(["show", f"{commit_b}:{dataset_dvc_file}"])
    return {"identical": hashlib.md5(a.encode()).hexdigest() == hashlib.md5(b.encode()).hexdigest()}

def has_data_changed():
    """Check via `dvc status` whether tracked data differs from what's recorded."""
    out = _run_dvc(["status"])
    return {"changed": "up to date" not in out.lower(), "raw": out}

def get_reproduction_instructions(commit: str):
    """Explain how to reproduce a dataset state at a given git commit/tag."""
    return f"git checkout {commit} && dvc checkout"