"""KnowledgeHub errors — 6xxx codes from common/errors."""

from __future__ import annotations

from typing import Any, Optional

from common.errors import ErrorCode

# Re-export 6xxx error codes
KNOWLEDGE_NOT_FOUND = ErrorCode.KNOWLEDGE_NOT_FOUND
KNOWLEDGE_INDEX_FAILED = ErrorCode.KNOWLEDGE_INDEX_FAILED
KNOWLEDGE_RETRIEVAL_FAILED = ErrorCode.KNOWLEDGE_RETRIEVAL_FAILED
KNOWLEDGE_UNAUTHORIZED = ErrorCode.KNOWLEDGE_UNAUTHORIZED


class KnowledgeHubError(Exception):
    """Base exception for KnowledgeHub errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.KNOWLEDGE_RETRIEVAL_FAILED,
        document_id: Optional[str] = None,
        **extra: Any,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.document_id = document_id


class KnowledgeNotFoundError(KnowledgeHubError):
    """Raised when a knowledge document is not found."""

    def __init__(self, document_id: str):
        super().__init__(
            f"Knowledge document not found: {document_id}",
            code=ErrorCode.KNOWLEDGE_NOT_FOUND,
            document_id=document_id,
        )


class KnowledgeIndexFailedError(KnowledgeHubError):
    """Raised when indexing a document fails."""

    def __init__(self, document_id: str, reason: str):
        super().__init__(
            f"Failed to index document '{document_id}': {reason}",
            code=ErrorCode.KNOWLEDGE_INDEX_FAILED,
            document_id=document_id,
        )


class KnowledgeRetrievalFailedError(KnowledgeHubError):
    """Raised when retrieval fails."""

    def __init__(self, reason: str):
        super().__init__(
            f"Retrieval failed: {reason}",
            code=ErrorCode.KNOWLEDGE_RETRIEVAL_FAILED,
        )


class KnowledgeUnauthorizedError(KnowledgeHubError):
    """Raised when access to a knowledge document is unauthorized."""

    def __init__(self, document_id: str, reason: str = "Access denied"):
        super().__init__(
            f"Unauthorized access to '{document_id}': {reason}",
            code=ErrorCode.KNOWLEDGE_UNAUTHORIZED,
            document_id=document_id,
        )
