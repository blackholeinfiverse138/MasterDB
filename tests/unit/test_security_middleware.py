"""
Unit Tests - Security Middleware & Role-Based Access Control
============================================================
Task ID: T-GOV-F01
Candidate: Ansh Gupta (Product Governance: BHIV)
"""

import pytest
from fastapi import HTTPException
from security.middleware import (
    UserRole,
    SecurityError,
    TokenReplayError,
    RoleUnauthorizedError,
    register_used_token,
    is_token_spent,
    reset_spent_tokens,
    require_role,
)


def test_token_replay_prevention():
    reset_spent_tokens()
    token = "auth_tok_session_98234729384729384"
    assert is_token_spent(token) is False

    # First registration must succeed
    result = register_used_token(token, metadata={"purpose": "governance_audit"})
    assert result is True
    assert is_token_spent(token) is True

    # Immediate replay must raise TokenReplayError
    with pytest.raises(TokenReplayError) as exc_info:
        register_used_token(token)
    assert exc_info.value.status_code == 409
    assert "Token replay detected" in str(exc_info.value)


def test_invalid_short_token_rejected():
    with pytest.raises(SecurityError) as exc_info:
        register_used_token("short")
    assert exc_info.value.status_code == 400


def test_reset_spent_tokens():
    token = "temp_tok_74938274982374982"
    register_used_token(token)
    assert is_token_spent(token) is True
    
    reset_spent_tokens()
    assert is_token_spent(token) is False


@pytest.mark.asyncio
async def test_require_role_authorized():
    checker = require_role([UserRole.GOVERNOR, UserRole.AUDITOR])
    # Case insensitive check
    role = await checker(x_role="governor", x_user_role=None, authorization=None)
    assert role == "governor"

    role2 = await checker(x_role=None, x_user_role="AUDITOR", authorization=None)
    assert role2 == "auditor"

    # Bearer token governor/admin detection
    role3 = await checker(x_role=None, x_user_role=None, authorization="Bearer governor_admin_token_xyz")
    assert role3 == "governor"


@pytest.mark.asyncio
async def test_require_role_bearer_consumer_fallback():
    checker = require_role([UserRole.CONSUMER])
    role = await checker(x_role=None, x_user_role=None, authorization="Bearer standard_user_tok")
    assert role == "consumer"


@pytest.mark.asyncio
async def test_require_role_unauthorized():
    checker = require_role([UserRole.GOVERNOR])
    with pytest.raises(HTTPException) as exc_info:
        await checker(x_role="consumer", x_user_role=None, authorization=None)
    assert exc_info.value.status_code == 403
    assert "Forbidden" in exc_info.value.detail
