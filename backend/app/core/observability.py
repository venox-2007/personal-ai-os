import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger("observability")
logger.setLevel(logging.INFO)
# Prevent propagation to root logger if desired, but we can leave it to keep it simple.

def log_execution_event(
    event_type: str,
    status: str,
    correlation_id: str,
    agent_name: Optional[str] = None,
    tool_name: Optional[str] = None,
    workflow_id: Optional[str] = None,
    step_id: Optional[str] = None,
    duration_ms: Optional[float] = None,
    error_category: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": event_type,
        "status": status,
        "correlation_id": correlation_id,
    }
    if agent_name: event["agent_name"] = agent_name
    if tool_name: event["tool_name"] = tool_name
    if workflow_id: event["workflow_id"] = workflow_id
    if step_id: event["step_id"] = step_id
    if duration_ms is not None: event["duration_ms"] = duration_ms
    if error_category: event["error_category"] = error_category
    if metadata:
        # scrub secrets
        safe_metadata = {}
        for k, v in metadata.items():
            if any(secret_word in k.lower() for secret_word in ["key", "secret", "token", "password", "auth"]):
                safe_metadata[k] = "***"
            else:
                safe_metadata[k] = v
        event["metadata"] = safe_metadata

    logger.info(f"[EXECUTION_EVENT] {json.dumps(event)}")
