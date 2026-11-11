import inspect
import json, logging, re, time, uuid, os
from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI
from agent.tools import dvc_tools, mlflow_tools, airflow_tools, kubernetes_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mlops_agent")

llm = OpenAI(api_key=os.environ["LLM_API_KEY"], base_url=os.environ["LLM_BASE_URL"])
MODEL = os.environ["LLM_MODEL"]

TOOLS = {
    "list_tracked_datasets": dvc_tools.list_tracked_datasets,
    "get_current_version": dvc_tools.get_current_version,
    "compare_versions": dvc_tools.compare_versions,
    "has_data_changed": dvc_tools.has_data_changed,
    "get_reproduction_instructions": dvc_tools.get_reproduction_instructions,
    "list_experiments": mlflow_tools.list_experiments,
    "list_runs": mlflow_tools.list_runs,
    "get_run_details": mlflow_tools.get_run_details,
    "get_best_run": mlflow_tools.get_best_run,
    "compare_runs": mlflow_tools.compare_runs,
    "get_model_versions": mlflow_tools.get_model_versions,
    "list_dags": airflow_tools.list_dags,
    "get_dag_run_status": airflow_tools.get_dag_run_status,
    "trigger_dag": airflow_tools.trigger_dag,
    "get_failed_tasks": airflow_tools.get_failed_tasks,
    "get_task_logs": airflow_tools.get_task_logs,
    "list_pods_and_deployments": kubernetes_tools.list_pods_and_deployments,
    "get_pod_status_and_logs": kubernetes_tools.get_pod_status_and_logs,
    "inspect_services": kubernetes_tools.inspect_services,
    "get_unhealthy_pods": kubernetes_tools.get_unhealthy_pods,
    "get_deployed_version": kubernetes_tools.get_deployed_version,
    "restart_deployment": kubernetes_tools.restart_deployment,
}

_TYPE_MAP = {str: "string", int: "integer", float: "number", bool: "boolean", list: "array"}

def _schema(name, fn):
    sig = inspect.signature(fn)
    properties, required = {}, []
    for pname, param in sig.parameters.items():
        annotation = param.annotation if param.annotation is not inspect.Parameter.empty else str
        base = getattr(annotation, "__origin__", annotation)
        json_type = _TYPE_MAP.get(base, "string")
        prop = {"type": json_type}
        if json_type == "array":
            prop["items"] = {"type": "string"}
        properties[pname] = prop
        if param.default is inspect.Parameter.empty:
            required.append(pname)
    return {"type": "function", "function": {
        "name": name, "description": (fn.__doc__ or name).strip(),
        "parameters": {"type": "object", "properties": properties, "required": required},
    }}

TOOL_SCHEMAS = [_schema(n, f) for n, f in TOOLS.items()]

SYSTEM_PROMPT = (
    "You are an MLOps assistant. Only state operational facts that came from a tool result. "
    "If a tool errors or a service is unavailable, say so explicitly rather than guessing. "
    "Never trigger retraining or any cluster-state change unless the user explicitly asked for it. "
    "Structure your final answer as: Known facts / Uncertainties / Recommendations."
)

MAX_TOOL_RESULT_CHARS = 1500

def _truncate(data):
    text = json.dumps(data)
    if len(text) > MAX_TOOL_RESULT_CHARS:
        return text[:MAX_TOOL_RESULT_CHARS] + "...(truncated)"
    return data

def _execute_tool(name, arguments, request_id):
    start = time.time()
    try:
        data, status, error = _truncate(TOOLS[name](**arguments)), "ok", None
    except Exception as e:
        data, status, error = None, "error", str(e)
    logger.info(json.dumps({"request_id": request_id, "tool": name, "status": status,
                             "duration_s": round(time.time() - start, 3)}))
    return {"status": status, "data": data, "error": error}

def handle_request(user_message: str) -> str:
    request_id = str(uuid.uuid4())
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_message}]

    for _ in range(16):
        for attempt in range(5):
            try:
                resp = llm.chat.completions.create(model=MODEL, messages=messages, tools=TOOL_SCHEMAS)
                break
            except Exception as e:
                if "429" in str(e) and attempt < 4:
                    wait = 30
                    match = re.search(r"try again in ([\d.]+)s", str(e))
                    if match:
                        wait = float(match.group(1)) + 1
                    time.sleep(wait)
                    continue
                raise
        choice = resp.choices[0]
        if not choice.message.tool_calls:
            return choice.message.content

        messages.append({
            "role": "assistant",
            "content": choice.message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"},
                }
                for tc in choice.message.tool_calls
            ],
        })
        for tc in choice.message.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                result = {"status": "error", "data": None, "error": "invalid tool arguments (not valid JSON)"}
            else:
                result = _execute_tool(tc.function.name, args, request_id)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})

    return "Reached tool-call limit without a final answer."