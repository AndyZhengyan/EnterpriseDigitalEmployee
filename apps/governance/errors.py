"""Governance service error codes — prefix 7xxx."""

from __future__ import annotations

from enum import Enum


class GovernanceErrorCode(Enum):
    """Governance-specific error codes (7xxx)."""

    PERMISSION_DENIED = (7001, "Permission denied")
    ROLE_NOT_FOUND = (7002, "Role not found")
    USER_NOT_FOUND = (7003, "User not found")
    INVALID_TOKEN = (7004, "Invalid or expired token")
    POLICY_VIOLATION = (7005, "ABAC policy violation")
    ROLE_ALREADY_EXISTS = (7006, "Role already exists")
    USER_ALREADY_ASSIGNED = (7007, "User already assigned to role")
    INVALID_ROLE_TRANSITION = (7008, "Invalid role transition")
    APPROVAL_REQUIRED = (7009, "High-risk operation requires approval")

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message}


class GovernanceError(Exception):
    """Base exception for governance service errors."""

    def __init__(self, message: str, code: int = 7000) -> None:
        self.message = message
        self.code = code
        super().__init__(message)
