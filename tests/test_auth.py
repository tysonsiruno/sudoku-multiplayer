"""
Test Authentication Functions
BUG #501-510 FIX: Automated testing
"""

import pytest
from server.auth import (
    hash_password,
    verify_password,
    validate_username,
    validate_email,
    validate_password,
    generate_access_token,
    decode_access_token
)


class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password(self):
        """Test password is hashed correctly"""
        password = "SecurePassword123!"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 0
        assert verify_password(password, hashed)

    def test_different_passwords_different_hashes(self):
        """Test same password creates different hashes each time"""
        password = "SecurePassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different due to salt
        assert hash1 != hash2

    def test_verify_wrong_password(self):
        """Test wrong password fails verification"""
        password = "SecurePassword123!"
        wrong_password = "WrongPassword456!"
        hashed = hash_password(password)

        assert not verify_password(wrong_password, hashed)


class TestUsernameValidation:
    """Test username validation rules"""

    def test_valid_username(self):
        """Test valid usernames pass"""
        valid_usernames = [
            "user123",
            "John_Doe",
            "player_1",
            "a" * 20  # Max length
        ]

        for username in valid_usernames:
            valid, msg = validate_username(username)
            assert valid, f"{username} should be valid: {msg}"

    def test_invalid_username_too_short(self):
        """Test username too short fails"""
        valid, msg = validate_username("ab")
        assert not valid
        assert "at least 3" in msg

    def test_invalid_username_too_long(self):
        """Test username too long fails"""
        valid, msg = validate_username("a" * 21)
        assert not valid
        assert "at most 20" in msg

    def test_invalid_username_consecutive_underscores(self):
        """Test consecutive underscores fail"""
        valid, msg = validate_username("user__name")
        assert not valid
        assert "consecutive underscores" in msg

    def test_invalid_username_starts_with_underscore(self):
        """Test username starting with underscore fails"""
        valid, msg = validate_username("_username")
        assert not valid
        assert "start with" in msg


class TestEmailValidation:
    """Test email validation"""

    def test_valid_email(self):
        """Test valid emails pass"""
        valid_emails = [
            "user@example.com",
            "john.doe@company.co.uk",
            "test+tag@domain.com"
        ]

        for email in valid_emails:
            valid, msg = validate_email(email)
            assert valid, f"{email} should be valid: {msg}"

    def test_invalid_email(self):
        """Test invalid emails fail"""
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user @example.com"
        ]

        for email in invalid_emails:
            valid, msg = validate_email(email)
            assert not valid, f"{email} should be invalid"


class TestPasswordValidation:
    """Test password validation rules"""

    def test_valid_password(self):
        """Test valid passwords pass"""
        valid_passwords = [
            "SecurePassword123!",
            "MyP@ssw0rd",
            "Test1234!@#$"
        ]

        for password in valid_passwords:
            valid, msg = validate_password(password)
            assert valid, f"{password} should be valid: {msg}"

    def test_invalid_password_too_short(self):
        """Test password too short fails"""
        valid, msg = validate_password("Short1!")
        assert not valid
        assert "at least 8" in msg

    def test_invalid_password_no_uppercase(self):
        """Test password without uppercase fails"""
        valid, msg = validate_password("lowercase123!")
        assert not valid
        assert "uppercase" in msg

    def test_invalid_password_no_lowercase(self):
        """Test password without lowercase fails"""
        valid, msg = validate_password("UPPERCASE123!")
        assert not valid
        assert "lowercase" in msg

    def test_invalid_password_no_number(self):
        """Test password without number fails"""
        valid, msg = validate_password("NoNumbers!")
        assert not valid
        assert "number" in msg

    def test_invalid_password_no_special(self):
        """Test password without special character fails"""
        valid, msg = validate_password("NoSpecial123")
        assert not valid
        assert "special character" in msg


class TestTokenGeneration:
    """Test JWT token generation and validation"""

    def test_generate_token(self):
        """Test token generation"""
        token = generate_access_token(1, "testuser")
        assert token is not None
        assert len(token) > 0

    def test_decode_token(self):
        """Test token decoding"""
        user_id = 123
        username = "testuser"

        token = generate_access_token(user_id, username)
        payload = decode_access_token(token)

        assert payload is not None
        assert payload['user_id'] == user_id
        assert payload['username'] == username
        assert 'jti' in payload
        assert 'exp' in payload

    def test_decode_invalid_token(self):
        """Test decoding invalid token returns None"""
        payload = decode_access_token("invalid.token.here")
        assert payload is None
