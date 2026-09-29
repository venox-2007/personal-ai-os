"""Approval management and decision endpoints."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.core.logging import logger
from app.orchestrator.orchestrator import orchestrator
from app.permissions.models import ApprovalStatus
from app.schemas.approval import (
    ApprovalDecisionRequest,
    ApprovalItemSchema,
    ApprovalExecutionResponse,
)
from app.services.approval_service import (
    approval_service,
    ApprovalNotFoundError,
    ApprovalAlreadyResolvedError,
    ApprovalExpiredError,
)

router = APIRouter(prefix="/approvals", tags=["Approvals"])


@router.get("", response_model=List[ApprovalItemSchema])
async def list_approvals(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by approval status (pending, approved, rejected, expired)")
) -> List[ApprovalItemSchema]:
    """Retrieves all authorization requests, optionally filtered by status."""
    parsed_status = None
    if status_filter:
        try:
            parsed_status = ApprovalStatus(status_filter.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status filter '{status_filter}'. Expected one of: {[s.value for s in ApprovalStatus]}",
            )

    requests = approval_service.list_requests(status=parsed_status)
    return [
        ApprovalItemSchema(
            id=r.id,
            tool_name=r.tool_name,
            tool_description=r.tool_description,
            permission_level=r.permission_level.value,
            permission_label=r.permission_level.label,
            arguments=r.arguments,
            action_description=r.action_description,
            status=r.status.value,
            created_at=r.created_at.isoformat(),
            expires_at=r.expires_at.isoformat(),
            resolved_at=r.resolved_at.isoformat() if r.resolved_at else None,
            resolution_reason=r.resolution_reason,
            conversation_id=r.conversation_id,
        )
        for r in requests
    ]


@router.get("/{approval_id}", response_model=ApprovalItemSchema)
async def get_approval(approval_id: str) -> ApprovalItemSchema:
    """Retrieves details of a specific approval request."""
    req = approval_service.get_request(approval_id)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request '{approval_id}' was not found.",
        )

    return ApprovalItemSchema(
        id=req.id,
        tool_name=req.tool_name,
        tool_description=req.tool_description,
        permission_level=req.permission_level.value,
        permission_label=req.permission_level.label,
        arguments=req.arguments,
        action_description=req.action_description,
        status=req.status.value,
        created_at=req.created_at.isoformat(),
        expires_at=req.expires_at.isoformat(),
        resolved_at=req.resolved_at.isoformat() if req.resolved_at else None,
        resolution_reason=req.resolution_reason,
        conversation_id=req.conversation_id,
    )


@router.post("/{approval_id}/approve", response_model=ApprovalExecutionResponse)
async def approve_request(
    approval_id: str,
    payload: ApprovalDecisionRequest = ApprovalDecisionRequest(),
) -> ApprovalExecutionResponse:
    """Confirms authorization for a pending action and resumes interrupted orchestrator execution."""
    try:
        conv_id, response_text, activities, tool_calls, execution_status, req = (
            await orchestrator.resolve_and_resume(
                approval_id=approval_id,
                approved=True,
                reason=payload.reason,
            )
        )
        return ApprovalExecutionResponse(
            approval_id=approval_id,
            status=execution_status,
            tool_name=req.tool_name,
            response=response_text,
            activities=activities,
            tool_calls=tool_calls,
            conversation_id=conv_id,
        )
    except ApprovalNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ApprovalAlreadyResolvedError, ApprovalExpiredError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error approving request {approval_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to authorize and resume action.",
        )


@router.post("/{approval_id}/reject", response_model=ApprovalExecutionResponse)
async def reject_request(
    approval_id: str,
    payload: ApprovalDecisionRequest = ApprovalDecisionRequest(),
) -> ApprovalExecutionResponse:
    """Declines authorization for a pending action, preventing execution and notifying the agent."""
    try:
        conv_id, response_text, activities, tool_calls, execution_status, req = (
            await orchestrator.resolve_and_resume(
                approval_id=approval_id,
                approved=False,
                reason=payload.reason,
            )
        )
        return ApprovalExecutionResponse(
            approval_id=approval_id,
            status=execution_status,
            tool_name=req.tool_name,
            response=response_text,
            activities=activities,
            tool_calls=tool_calls,
            conversation_id=conv_id,
        )
    except ApprovalNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ApprovalAlreadyResolvedError, ApprovalExpiredError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error rejecting request {approval_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject action.",
        )
