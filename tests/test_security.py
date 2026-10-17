import uuid

import pytest
from fastapi import HTTPException

from app.core.security import create_access_token, decode_token, hash_password, verify_password


def test_password_roundtrip():
    h = hash_password("correct horse")
    assert verify_password("correct horse", h) and not verify_password("wrong", h)


def test_token_roundtrip_and_tamper():
    uid = uuid.uuid4()
    token = create_access_token(uid)
    assert decode_token(token) == uid
    with pytest.raises(HTTPException):
        decode_token(token + "x")
