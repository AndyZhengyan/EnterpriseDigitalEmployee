"""SkillHub errors — 5xxx codes from common/errors."""

from __future__ import annotations

from typing import Any, Optional

from common.errors import ErrorCode

# Re-export 5xxx error codes
SKILL_NOT_FOUND = ErrorCode.SKILL_NOT_FOUND
SKILL_INVOCATION_FAILED = ErrorCode.SKILL_INVOCATION_FAILED
SKILL_NOT_APPLICABLE = ErrorCode.SKILL_NOT_APPLICABLE
SKILL_DEPRECATED = ErrorCode.SKILL_DEPRECATED


class SkillHubError(Exception):
    """Base exception for SkillHub errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.SKILL_INVOCATION_FAILED,
        skill_id: Optional[str] = None,
        **extra: Any,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.skill_id = skill_id


class SkillNotFoundError(SkillHubError):
    """Raised when a skill ID is not found."""

    def __init__(self, skill_id: str):
        super().__init__(
            f"Skill not found: {skill_id}",
            code=ErrorCode.SKILL_NOT_FOUND,
            skill_id=skill_id,
        )


class SkillInvocationFailedError(SkillHubError):
    """Raised when skill invocation fails."""

    def __init__(self, skill_id: str, reason: str):
        super().__init__(
            f"Skill '{skill_id}' invocation failed: {reason}",
            code=ErrorCode.SKILL_INVOCATION_FAILED,
            skill_id=skill_id,
        )


class SkillNotApplicableError(SkillHubError):
    """Raised when a skill is not applicable to the current task."""

    def __init__(self, skill_id: str, reason: str):
        super().__init__(
            f"Skill '{skill_id}' not applicable: {reason}",
            code=ErrorCode.SKILL_NOT_APPLICABLE,
            skill_id=skill_id,
        )


class SkillDeprecatedError(SkillHubError):
    """Raised when attempting to invoke a deprecated skill."""

    def __init__(self, skill_id: str):
        super().__init__(
            f"Skill '{skill_id}' is deprecated",
            code=ErrorCode.SKILL_DEPRECATED,
            skill_id=skill_id,
        )
