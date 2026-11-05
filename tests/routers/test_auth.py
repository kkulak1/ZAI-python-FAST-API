import unittest
from unittest.mock import MagicMock, patch

from schemas import LoginRequest, PasswordChange
from routers import auth


class AuthRouterTests(unittest.TestCase):
    @patch("routers.auth.issue_token", return_value="token")
    @patch("routers.auth.authenticate_user")
    def test_login_authenticates_user_and_returns_token(self, authenticate, issue):
        user = MagicMock(id=7)
        authenticate.return_value = user

        result = auth.login(LoginRequest(username="admin", password="secret"), MagicMock())

        authenticate.assert_called_once()
        issue.assert_called_once_with(user, 3600)
        self.assertEqual(result.accessToken, "token")
        self.assertEqual(result.tokenType, "Bearer")
        self.assertEqual(result.expiresIn, 3600)

    @patch("routers.auth.revoke_token")
    def test_logout_revokes_bearer_token(self, revoke):
        credentials = MagicMock(credentials="token")

        response = auth.logout(_admin=MagicMock(), credentials=credentials)

        revoke.assert_called_once_with("token")
        self.assertEqual(response.status_code, 204)

    @patch("routers.auth.change_password")
    def test_update_password_delegates_to_security_service(self, change):
        user = MagicMock()
        db = MagicMock()
        payload = PasswordChange(currentPassword="old-password", newPassword="new-password")

        response = auth.update_password(payload, db, user)

        change.assert_called_once_with(db, user, "old-password", "new-password")
        self.assertEqual(response.status_code, 204)


if __name__ == "__main__":
    unittest.main()
