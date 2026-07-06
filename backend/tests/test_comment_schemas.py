import pytest
from pydantic import ValidationError

from app.schemas.comment import CommentCreateRequest


def test_comment_over_2000_chars_rejected():
    with pytest.raises(ValidationError):
        CommentCreateRequest(comment="a" * 2001)


def test_comment_under_10_chars_rejected():
    with pytest.raises(ValidationError):
        CommentCreateRequest(comment="short")


def test_comment_within_bounds_accepted():
    req = CommentCreateRequest(comment="a" * 500)
    assert len(req.comment) == 500