"""Tests for Permission hierarchy and approval validation."""

import pytest
from app.permissions.levels import PermissionLevel
from app.permissions.models import ApprovalRequest, ApprovalStatus, PermissionContext


def test_permission_level_hierarchy():
    """Verify numeric levels and ordering."""
    assert PermissionLevel.LEVEL_0_READ_ONLY == 0
    assert PermissionLevel.LEVEL_1_LOW_IMPACT == 1
    assert PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT == 2
    assert PermissionLevel.LEVEL_3_DESTRUCTIVE == 3


def test_permission_approval_requirements():
    """Verify approval defaults for levels 2 and 3."""
    assert PermissionLevel.LEVEL_0_READ_ONLY.requires_approval_default is False
    assert PermissionLevel.LEVEL_1_LOW_IMPACT.requires_approval_default is False
    assert PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT.requires_approval_default is True
    assert PermissionLevel.LEVEL_3_DESTRUCTIVE.requires_approval_default is True


def test_permission_context_evaluation():
    """Verify dynamic context evaluation."""
    ctx = PermissionContext(require_level_2_approval=True, require_level_3_approval=True)
    assert ctx.requires_approval(PermissionLevel.LEVEL_0_READ_ONLY) is False
    assert ctx.requires_approval(PermissionLevel.LEVEL_1_LOW_IMPACT) is False
    assert ctx.requires_approval(PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT) is True
    assert ctx.requires_approval(PermissionLevel.LEVEL_3_DESTRUCTIVE) is True


def test_approval_request_model():
    """Verify approval request construction."""
    req = ApprovalRequest(
        tool_name="send_email",
        permission_level=PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT,
        action_description="Send response to recruiter",
        parameters={"to": "recruiter@example.com"},
    )
    assert req.status == ApprovalStatus.PENDING
    assert req.id is not None
    assert req.requested_at is not None
