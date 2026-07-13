"""
Exceptions raised by CommentService.

Same pattern as flow_exceptions.py (B-12) — these already exist (or should
exist) in Parthiv's shared hierarchy; duplicated locally so this branch has
no import-order dependency on his branch. Dedupe at merge time:

  - SessionNotFoundError        -> Parthiv's SessionException tree.
  - InsufficientPermissionsError -> Parthiv's AuthException tree (403).
  - CommentNotFoundError        -> genuinely new, not in backend-arch.md's
    Section 14.1 hierarchy, but api-spec.md Section 11 error catalog
    already lists COMMENT_NOT_FOUND / 404 — so the *code* is spec'd even
    though the exception class isn't. Same kind of gap as
    DFVNotUnlockedError was on B-12 — flag it for exceptions/base.py.

Spec conflict to flag in the PR (see comment_service.py docstring for
detail): api-spec.md Section 6.1 says a mentor commenting on an
unassigned team's session gets 403 INSUFFICIENT_PERMISSIONS, but
rbac.md's edge case R11 says it should be 404 SESSION_NOT_FOUND (resource
filter hides the session before the comment check runs) — same as how
GET/session access works elsewhere. I've implemented the 403 per the Day 3
acceptance criteria as written, but this needs a decision from whoever
owns api-spec.md / rbac.md.
"""

from __future__ import annotations


class CommentServiceError(Exception):
    error_code: str = "COMMENT_SERVICE_ERROR"
    status_code: int = 500


class SessionNotFoundError(CommentServiceError):
    error_code = "SESSION_NOT_FOUND"
    status_code = 404

    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"No session found with id '{session_id}'")


class InsufficientPermissionsError(CommentServiceError):
    error_code = "INSUFFICIENT_PERMISSIONS"
    status_code = 403

    def __init__(self, message: str = "You do not have permission to do this"):
        super().__init__(message)


class CommentNotFoundError(CommentServiceError):
    error_code = "COMMENT_NOT_FOUND"
    status_code = 404

    def __init__(self, comment_id: str):
        self.comment_id = comment_id
        super().__init__(f"No comment found with id '{comment_id}'")