from app.services.auth_service import hash_password, verify_password, create_access_token, decode_access_token


def test_password_hash_and_verify():
    plain = "my-secret-password-123"
    hashed = hash_password(plain)

    assert hashed != plain  # 평문 그대로 저장되면 안 됨
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_jwt_token_roundtrip():
    token = create_access_token(user_id=42)
    decoded_user_id = decode_access_token(token)

    assert decoded_user_id == 42


def test_jwt_invalid_token():
    assert decode_access_token("this-is-not-a-valid-token") is None
