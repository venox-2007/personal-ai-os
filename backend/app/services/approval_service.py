"""Approval service managing human-in-the-loop authorization requests and lifecycles."""

from datetime import datetime, timezone, timedelta
import json
from typing import Any, Dict, List, Optional
import uuid

from app.core.config import settings
from app.core.logging import logger
from app.database.session import SessionLocal
from app.models.entities import ApprovalRequestModel
from app.permissions.levels import PermissionLevel
from app.permissions.models import ApprovalRequest, ApprovalStatus


class ApprovalServiceError(Exception):
    """Base exception for approval service errors."""
    pass


class ApprovalNotFoundError(ApprovalServiceError):
    """Raised when the requested approval ID does not exist."""
    pass


class ApprovalAlreadyResolvedError(ApprovalServiceError):
    """Raised when attempting to approve/reject an already resolved request."""
    pass


class ApprovalExpiredError(ApprovalServiceError):
    """Raised when an approval request has exceeded its expiry window."""
    pass


class ApprovalService:
    """Service handling creation, state transitions, expiration, and queries for approvals.

    Stores approval state in SQLite with in-memory caching to ensure durability
    across API requests without external broker dependencies.
    """

    def __init__(self, expiry_seconds: Optional[int] = None) -> None:
        self.expiry_seconds = expiry_seconds or getattr(settings, "APPROVAL_EXPIRY_SECONDS", 300)
        self._memory_cache: Dict[str, ApprovalRequest] = {}

    def _sync_to_db(self, req: ApprovalRequest) -> None:
        """Persists or updates an approval request in SQLite."""
        try:
            with SessionLocal() as db:
                db_model = db.query(ApprovalRequestModel).filter(ApprovalRequestModel.id == req.id).first()
                if not db_model:
                    db_model = ApprovalRequestModel(
                        id=req.id,
                        conversation_id=req.conversation_id,
                        tool_name=req.tool_name,
                        permission_level=req.permission_level.value,
                        action_description=req.action_description,
                        arguments_json=json.dumps(req.arguments),
                        status=req.status.value,
                        requested_at=req.created_at,
                        expires_at=req.expires_at,
                        decided_at=req.resolved_at,
                        resolution_reason=req.resolution_reason,
                        execution_context_json=json.dumps(req.execution_context) if req.execution_context else None,
                    )
                    db.add(db_model)
                else:
                    db_model.status = req.status.value
                    db_model.decided_at = req.resolved_at
                    db_model.resolution_reason = req.resolution_reason
                db.commit()
        except Exception as e:
            logger.debug(f"Approval DB persistence notice (using cache): {e}")

    def create_request(
        self,
        tool_name: str,
        permission_level: PermissionLevel,
        arguments: Dict[str, Any],
        action_description: str,
        tool_description: str = "",
        conversation_id: Optional[str] = None,
        execution_context: Optional[Dict[str, Any]] = None,
        expires_in_seconds: Optional[int] = None,
    ) -> ApprovalRequest:
        """Creates and stores a new pending approval request."""
        ttl = expires_in_seconds or self.expiry_seconds
        now = datetime.now(timezone.utc)
        req = ApprovalRequest(
            id=str(uuid.uuid4()),
            tool_name=tool_name,
            tool_description=tool_description,
            permission_level=permission_level,
            arguments=arguments,
            action_description=action_description,
            status=ApprovalStatus.PENDING,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl),
            conversation_id=conversation_id,
            execution_context=execution_context or {},
        )

        self._memory_cache[req.id] = req
        self._sync_to_db(req)
        logger.info(f"Created approval request {req.id} for tool '{tool_name}' (Level {permission_level.value})")
        return req

    def get_request(self, approval_id: str) -> Optional[ApprovalRequest]:
        """Retrieves an approval request and checks for expiration."""
        req = self._memory_cache.get(approval_id)

        # Check DB if not found in memory cache
        if not req:
            try:
                with SessionLocal() as db:
                    row = db.query(ApprovalRequestModel).filter(ApprovalRequestModel.id == approval_id).first()
                    if row:
                        req = ApprovalRequest(
                            id=row.id,
                            tool_name=row.tool_name,
                            permission_level=PermissionLevel(row.permission_level),
                            action_description=row.action_description,
                            arguments=json.loads(row.arguments_json) if row.arguments_json else {},
                            status=ApprovalStatus(row.status),
                            created_at=row.requested_at,
                            expires_at=row.expires_at or (row.requested_at + timedelta(seconds=self.expiry_seconds)),
                            resolved_at=row.decided_at,
                            resolution_reason=row.resolution_reason,
                            conversation_id=row.conversation_id,
                            execution_context=json.loads(row.execution_context_json) if row.execution_context_json else {},
                        )
                        self._memory_cache[req.id] = req
            except Exception as e:
                logger.debug(f"Failed to query approval from DB: {e}")

        if not req:
            return None

        # Check for expiration transition
        if req.status == ApprovalStatus.PENDING and datetime.now(timezone.utc) > req.expires_at:
            req.status = ApprovalStatus.EXPIRED
            req.resolved_at = datetime.now(timezone.utc)
            req.resolution_reason = "Approval request expired automatically after timeout."
            self._sync_to_db(req)
            logger.info(f"Approval request {req.id} expired.")

        return req

    def list_requests(self, status: Optional[ApprovalStatus] = None) -> List[ApprovalRequest]:
        """Returns all approval requests, optionally filtered by status."""
        # Refresh all pending requests in cache for expiration
        for req in list(self._memory_cache.values()):
            self.get_request(req.id)

        requests = list(self._memory_cache.values())
        if status:
            requests = [r for r in requests if r.status == status]

        return sorted(requests, key=lambda r: r.created_at, reverse=True)

    def approve_request(
        self,
        approval_id: str,
        reason: Optional[str] = None,
        decided_by: Optional[str] = "user",
    ) -> ApprovalRequest:
        """Transitions request to APPROVED after strict validation."""
        req = self.get_request(approval_id)
        if not req:
            raise ApprovalNotFoundError(f"Approval request '{approval_id}' was not found.")

        if req.status == ApprovalStatus.EXPIRED or (
            req.status == ApprovalStatus.PENDING and datetime.now(timezone.utc) > req.expires_at
        ):
            req.status = ApprovalStatus.EXPIRED
            self._sync_to_db(req)
            raise ApprovalExpiredError(f"Approval request '{approval_id}' has expired.")

        if req.status != ApprovalStatus.PENDING:
            raise ApprovalAlreadyResolvedError(
                f"Approval request '{approval_id}' is already resolved with status '{req.status.value}'."
            )

        req.status = ApprovalStatus.APPROVED
        req.resolved_at = datetime.now(timezone.utc)
        req.resolution_reason = reason or "Approved by user"
        self._sync_to_db(req)
        logger.info(f"Approval request {approval_id} APPROVED by {decided_by}.")
        return req

    def reject_request(
        self,
        approval_id: str,
        reason: Optional[str] = None,
        decided_by: Optional[str] = "user",
    ) -> ApprovalRequest:
        """Transitions request to REJECTED after strict validation."""
        req = self.get_request(approval_id)
        if not req:
            raise ApprovalNotFoundError(f"Approval request '{approval_id}' was not found.")

        if req.status == ApprovalStatus.EXPIRED or (
            req.status == ApprovalStatus.PENDING and datetime.now(timezone.utc) > req.expires_at
        ):
            req.status = ApprovalStatus.EXPIRED
            self._sync_to_db(req)
            raise ApprovalExpiredError(f"Approval request '{approval_id}' has expired.")

        if req.status != ApprovalStatus.PENDING:
            raise ApprovalAlreadyResolvedError(
                f"Approval request '{approval_id}' is already resolved with status '{req.status.value}'."
            )

        req.status = ApprovalStatus.REJECTED
        req.resolved_at = datetime.now(timezone.utc)
        req.resolution_reason = reason or "Rejected by user"
        self._sync_to_db(req)
        logger.info(f"Approval request {approval_id} REJECTED by {decided_by}.")
        return req

    def clear(self) -> None:
        """Resets the service cache (primarily for unit tests)."""
        self._memory_cache.clear()


# Global default instance
approval_service = ApprovalService()
