import unittest
from unittest.mock import MagicMock, patch

from flask import Flask, request, session
from favorites import register_favorite_routes


class FavoritesTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'test-only'
        self.app.testing = True

        def payload():
            if request.headers.get('X-CSRF-Token') != session.get('csrf_token'):
                return None
            return request.get_json(silent=True)

        register_favorite_routes(self.app, {}, {'tourism': 'tourist_landmarks', 'food': 'food_landmarks', 'event': 'event_landmarks'}, payload)
        self.client = self.app.test_client()
        self.conn = MagicMock()
        self.cur = self.conn.cursor.return_value.__enter__.return_value
        self.patch = patch('favorites.pymysql.connect', return_value=self.conn)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def login(self):
        with self.client.session_transaction() as session:
            session.update(member_id=7, csrf_token='token')

    def save(self, **changes):
        data = dict(category='tourism', landmark_id=4, active=True)
        data.update(changes)
        return self.client.post('/api/favorites', json=data, headers={'X-CSRF-Token': 'token'})

    def test_login_required(self):
        self.assertEqual(self.client.get('/api/favorites').status_code, 401)
        self.assertEqual(self.save().status_code, 401)
        self.conn.cursor.assert_not_called()

    def test_csrf_and_input_validation(self):
        self.login()
        self.assertEqual(self.client.post('/api/favorites', json={}).status_code, 400)
        for data in [dict(category=[]), dict(category='invalid'), dict(landmark_id=True),
                     dict(landmark_id=-1), dict(landmark_id='4'), dict(active='true')]:
            self.assertEqual(self.save(**data).status_code, 400)
        self.conn.cursor.assert_not_called()

    def test_add_is_idempotent_and_owned_by_session(self):
        self.login()
        self.cur.fetchone.return_value = {'id': 4}
        self.assertEqual(self.save().status_code, 200)
        sql, args = self.cur.execute.call_args.args
        self.assertIn('ON DUPLICATE KEY UPDATE', sql)
        self.assertEqual(args, (7, 'tourism', 4))
        self.conn.commit.assert_called_once()

    def test_missing_landmark_is_not_saved(self):
        self.login()
        self.cur.fetchone.return_value = None
        self.assertEqual(self.save().status_code, 404)
        self.conn.commit.assert_not_called()

    def test_remove_only_deletes_current_members_record(self):
        self.login()
        self.assertEqual(self.save(active=False).status_code, 200)
        sql, args = self.cur.execute.call_args.args
        self.assertIn('DELETE FROM member_favorites WHERE member_id=%s', sql)
        self.assertEqual(args, (7, 'tourism', 4))

    def test_coordinate_free_places_remain_in_favorites(self):
        self.login()
        for category in ['tourism', 'event']:
            with self.subTest(category=category):
                self.cur.fetchall.side_effect = [
                    [dict(id=4, title='Place', description='Info', latitude=None, longitude=None,
                          location_url='https://example.com', source_name='Source', locality_name='City')]
                    if kind == category else [] for kind in ['tourism', 'food', 'event']
                ] + [[]]
                response = self.client.get('/api/favorites')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json['landmarks'][0]['category'], category)
                self.assertIsNone(response.json['landmarks'][0]['latitude'])
                self.assertIsNone(response.json['landmarks'][0]['longitude'])

    def test_list_joins_live_places_and_separates_categories(self):
        self.login()
        self.cur.fetchall.side_effect = [
            [dict(id=4, title='Place', description='Info', latitude='37.5', longitude='127.1',
                  location_url='', source_name='Source', locality_name='City')], [], [], []]
        response = self.client.get('/api/favorites')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['landmarks'][0]['category'], 'tourism')
        self.assertEqual(response.json['landmarks'][0]['latitude'], 37.5)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        for call, category in zip(self.cur.execute.call_args_list[1:], ['tourism', 'food', 'event']):
            self.assertIn('JOIN', call.args[0])
            self.assertEqual(call.args[1], (7, category))


if __name__ == '__main__':
    unittest.main()
