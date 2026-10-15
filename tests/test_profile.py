import unittest
from unittest.mock import MagicMock, patch

from app import app, TRAVEL_STYLES
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        with self.client.session_transaction() as session:
            session.update(member_id=7, csrf_token='test-token')
        self.conn = MagicMock()
        self.cur = self.conn.cursor.return_value.__enter__.return_value
        self.old_hash = generate_password_hash('old-password')
        self.cur.fetchone.return_value = dict(id=7, username='old_user', password_hash=self.old_hash)
        self.mock_connection = patch('app.member_connection', return_value=self.conn)
        self.mock_connection.start()
        self.addCleanup(self.mock_connection.stop)

    def save(self, **changes):
        data = dict(name='테스트', birth_date='2000-01-01', address='서울', mbti='INFP',
                    travel_styles=[TRAVEL_STYLES[0]], username='new_user',
                    current_password='old-password', password='new-password',
                    password_confirmation='new-password')
        data.update(changes)
        return self.client.post('/api/profile', json=data, headers={'X-CSRF-Token': 'test-token'})

    def test_updates_credentials_with_hashed_password(self):
        self.assertEqual(self.save().status_code, 200)
        args = self.cur.execute.call_args.args[1]
        self.assertEqual(args[0], 'new_user')
        self.assertTrue(check_password_hash(args[1], 'new-password'))
        self.assertEqual(args[-1], 7)
        self.conn.commit.assert_called_once()

    def test_same_password_rejects_entire_update(self):
        response = self.save(password='old-password', password_confirmation='old-password')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['code'], 'same_password')
        self.assertEqual(self.cur.execute.call_count, 1)
        self.conn.commit.assert_not_called()

    def test_wrong_current_password(self):
        self.assertEqual(self.save(current_password='wrong-password').status_code, 400)
        self.conn.commit.assert_not_called()

    def test_blank_password_preserves_hash(self):
        self.assertEqual(self.save(password='', password_confirmation='').status_code, 200)
        self.assertEqual(self.cur.execute.call_args.args[1][1], self.old_hash)

    def test_duplicate_username(self):
        self.cur.execute.side_effect = [None, pymysql.IntegrityError(1062, 'duplicate')]
        self.assertEqual(self.save().status_code, 409)
        self.conn.commit.assert_not_called()

    def test_confirmation_mismatch(self):
        self.assertEqual(self.save(password_confirmation='different-password').status_code, 400)
        self.conn.commit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
