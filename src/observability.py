"""Simple observability utilities: logs, traces, and metrics (file-backed for demo)."""
import json, os, time
from typing import Dict, Any, List
LOG_PATH = 'data/processed/agent_logs.jsonl'
TRACE_PATH = 'data/processed/agent_traces.jsonl'
METRICS_PATH = 'data/processed/agent_metrics.json'

def log_event(event: Dict[str, Any]):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, 'a') as f:
        f.write(json.dumps({**event, 'ts': time.time()}) + '\n')

def trace_span(span: Dict[str, Any]):
    os.makedirs(os.path.dirname(TRACE_PATH), exist_ok=True)
    with open(TRACE_PATH, 'a') as f:
        f.write(json.dumps({**span, 'ts': time.time()}) + '\n')

def emit_metric(name: str, value: float, labels: Dict[str, str] = None):
    os.makedirs(os.path.dirname(METRICS_PATH), exist_ok=True)
    if os.path.exists(METRICS_PATH):
        with open(METRICS_PATH, 'r') as f:
            metrics = json.load(f)
    else:
        metrics = {}
    metrics[name] = {'value': value, 'labels': labels or {}, 'ts': time.time()}
    with open(METRICS_PATH, 'w') as f:
        json.dump(metrics, f, indent=2)
