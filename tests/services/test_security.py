import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from database.models import User
from services import security


class SecurityServiceTests(unittest.TestCase):
    def test_verify_password_returns_true_for_matching_password(self):
        password_hash = security.hash_password("correct-password")

        self.assertTrue(security.verify_password("correct-password", password_hash))

    def test_verify_password_returns_false_for_wrong_password(self):
        password_hash = security.hash_password("correct-password")

        self.assertFalse(security.verify_password("wrong-password", password_hash))

    def test_verify_password_returns_false_for_invalid_hash(self):
        self.assertFalse(security.verify_password("password", "invalid-hash"))

    @patch("services.security.verify_password", return_value=True)
    def test_authenticate_user_returns_matching_user(self, verify):
        db = MagicMock()
        user = User(id=3, username="admin", password_hash="password-hash")
        db.scalar.return_value = user

        result = security.authenticate_user(db, "admin", "password")

        self.assertIs(result, user)
        verify.assert_called_once_with("password", "password-hash")
        db.scalar.assert_called_once()

    @patch("services.security.verify_password", return_value=False)
    def test_authenticate_user_rejects_invalid_password(self, verify):
        db = MagicMock()
        db.scalar.return_value = User(id=3, username="admin", password_hash="password-hash")

        with self.assertRaisesRegex(HTTPException, "Invalid credentials"):
            security.authenticate_user(db, "admin", "wrong-password")

    def test_authenticate_user_rejects_unknown_user(self):
        db = MagicMock()
        db.scalar.return_value = None

        with self.assertRaisesRegex(HTTPException, "Invalid credentials"):
            security.authenticate_user(db, "unknown", "password")

    def test_issue_token_and_get_current_user_round_trip(self):
        user = User(id=7, username="admin", password_hash="password-hash")
        db = MagicMock()
        db.get.return_value = user

        token = security.issue_token(user, expires_in=60)

        self.assertIs(security.get_current_user(db, token), user)
        db.get.assert_called_once_with(User, 7)

    def test_get_current_user_rejects_missing_token(self):
        with self.assertRaisesRegex(HTTPException, "Authentication required"):
            security.get_current_user(MagicMock(), None)

    def test_get_current_user_rejects_invalid_signature(self):
        user = User(id=7, username="admin", password_hash="password-hash")
        token = security.issue_token(user) + "invalid"

        with self.assertRaisesRegex(HTTPException, "Invalid token"):
            security.get_current_user(MagicMock(), token)

    def test_get_current_user_rejects_unknown_user(self):
        db = MagicMock()
        db.get.return_value = None
        token = security.issue_token(User(id=7, username="admin", password_hash="password-hash"))

        with self.assertRaisesRegex(HTTPException, "Invalid token"):
            security.get_current_user(db, token)

    @patch("services.security.time.time", return_value=2_000_000_000)
    def test_get_current_user_rejects_expired_token(self, _time):
        user = User(id=7, username="admin", password_hash="password-hash")
        token = security.issue_token(user, expires_in=-1)

        with self.assertRaisesRegex(HTTPException, "Invalid token"):
            security.get_current_user(MagicMock(), token)

    def test_revoked_token_is_rejected(self):
        user = User(id=8, username="admin", password_hash="password-hash")
        db = MagicMock()
        db.get.return_value = user
        token = security.issue_token(user)

        security.revoke_token(token)

        with self.assertRaisesRegex(HTTPException, "revoked"):
            security.get_current_user(db, token)

    def test_revoke_token_ignores_invalid_token(self):
        security.revoke_token("not-a-token")

    @patch("services.security.verify_password", return_value=False)
    def test_change_password_rejects_wrong_current_password(self, verify):
        user = User(id=1, username="admin", password_hash="old-hash")

        with self.assertRaisesRegex(HTTPException, "Current password is incorrect"):
            security.change_password(MagicMock(), user, "wrong", "new")

    @patch("services.security.hash_password", return_value="new-hash")
    @patch("services.security.verify_password", return_value=True)
    def test_change_password_updates_hash_and_commits(self, verify, hash_password):
        db = MagicMock()
        user = User(id=1, username="admin", password_hash="old-hash")

        security.change_password(db, user, "old", "new")

        verify.assert_called_once_with("old", "old-hash")
        hash_password.assert_called_once_with("new")
        self.assertEqual(user.password_hash, "new-hash")
        db.commit.assert_called_once()

    def test_create_sensor_key_returns_url_safe_key(self):
        key = security.create_sensor_key()

        self.assertIsInstance(key, str)
        self.assertGreaterEqual(len(key), 32)

    def test_verify_sensor_api_key_returns_sensor(self):
        db = MagicMock()
        sensor = MagicMock()
        db.scalar.return_value = sensor

        result = security.verify_sensor_api_key(db, "sensor-key")

        self.assertIs(result, sensor)
        db.scalar.assert_called_once()

    def test_verify_sensor_api_key_rejects_unknown_key(self):
        db = MagicMock()
        db.scalar.return_value = None

        with self.assertRaisesRegex(HTTPException, "Invalid API key"):
            security.verify_sensor_api_key(db, "unknown-key")


if __name__ == "__main__":
    unittest.main()
