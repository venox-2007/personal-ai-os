"""Chat endpoint for communicating with the central Orchestrator."""

from fastapi import APIRouter, HTTPException
from app.core.logging import logger
from app.schemas.chat import ChatRequest, ChatResponse
from app.orchestrator.orchestrator import orchestrator

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def chat_with_orchestrator(request: ChatRequest) -> ChatResponse:
    """Sends a user message to the central Orchestrator Agent.

    Returns the orchestrator's synthesized response along with observable activity events, tool execution data, and any pending approval requests.
    """
    try:
        conv_id, response_text, activities, tool_calls, status, approval_dict = await orchestrator.handle_message(
            message=request.message,
            conversation_id=request.conversation_id,
        )
        return ChatResponse(
            conversation_id=conv_id,
            response=response_text,
            activities=activities,
            tool_calls=tool_calls,
            status=status,
            approval=approval_dict,
            metadata={"source": "orchestrator_agent"},
        )
    except Exception as e:
        logger.error(f"Error handling chat request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
