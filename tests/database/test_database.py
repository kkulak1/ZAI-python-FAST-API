import unittest
from unittest.mock import MagicMock, patch

from database.database import get_db


class GetDbTests(unittest.TestCase):
    @patch("database.database.SessionLocal")
    def test_yields_session_and_closes_it(self, session_local):
        session = MagicMock()
        session_local.return_value = session

        database_session = get_db()

        self.assertIs(next(database_session), session)
        database_session.close()

        session_local.assert_called_once_with()
        session.close.assert_called_once_with()

    @patch("database.database.SessionLocal")
    def test_closes_session_when_dependency_raises(self, session_local):
        session = MagicMock()
        session_local.return_value = session
        database_session = get_db()

        next(database_session)
        with self.assertRaises(RuntimeError):
            database_session.throw(RuntimeError("request failed"))

        session.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
