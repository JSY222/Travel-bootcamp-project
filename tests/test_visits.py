import io
import unittest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

from flask import Flask
from visits import register_visit_routes


class VisitsTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'test-only'
        self.app.testing = True
        register_visit_routes(self.app, {}, {'tourism': 'tourist_landmarks', 'food': 'food_landmarks', 'event': 'event_landmarks'})
        self.client = self.app.test_client()
        self.conn = MagicMock()
        self.cur = self.conn.cursor.return_value.__enter__.return_value
        self.db = patch('visits.pymysql.connect', return_value=self.conn)
        self.db.start()
        self.addCleanup(self.db.stop)
        self.rankings = patch('visits.ranking_places', return_value=[])
        self.rankings.start()
        self.addCleanup(self.rankings.stop)
        self.awards = patch('visits.award_stamp_points', return_value=100)
        self.awards.start()
        self.addCleanup(self.awards.stop)
        self.points = patch('visits.total_points', return_value=100)
        self.points_mock = self.points.start()
        self.addCleanup(self.points.stop)

    def login(self):
        with self.client.session_transaction() as session:
            session.update(member_id=7, csrf_token='token')

    def save(self, **changes):
        data = dict(category='tourism', landmark_id='4', review='A good visit', visited_on='2026-01-01',
                    photo=(io.BytesIO(b'\x89PNG\r\n\x1a\nphoto'), 'photo.png'))
        data.update(changes)
        return self.client.post('/api/visits', data=data, headers={'X-CSRF-Token': 'token'})

    def test_stamp_ranking_ties_and_private_fields(self):
        self.login()
        self.points_mock.side_effect = [500, 500, 200]
        self.cur.fetchall.side_effect = [[dict(id=1, name='Alice', stamp_count=5),
            dict(id=2, name='Bob', stamp_count=5), dict(id=7, name='Mine', stamp_count=2)],
            [dict(id=1, category='food', region_code='11', locality_name='City')],
            [dict(member_id=7, category='food', landmark_id=1)]]
        result = self.client.get('/api/stamps/ranking')
        self.assertEqual(result.status_code, 200)
        self.assertEqual([r['rank'] for r in result.json['ranking']], [1, 1, 3])
        self.assertEqual(result.json['my_rank']['stamp_count'], 2)
        self.assertEqual(result.json['my_rank']['name'], '나')
        self.assertEqual(result.json['progress']['silver'], dict(earned=1, total=1))
        self.assertNotIn('id', result.json['ranking'][0])
        self.assertNotEqual(result.json['ranking'][0]['name'], 'Alice')
        self.assertEqual(result.headers['Cache-Control'], 'no-store')

    def test_guest_cannot_read_write_or_view_photo(self):
        self.assertEqual(self.client.get('/api/visits').status_code, 401)
        self.assertEqual(self.save().status_code, 401)
        self.assertEqual(self.client.get('/api/visits/1/photo').status_code, 401)
        self.conn.cursor.assert_not_called()

    def test_csrf_required(self):
        self.login()
        self.assertEqual(self.client.post('/api/visits', data={}).status_code, 400)
        self.conn.cursor.assert_not_called()

    def test_input_and_file_validation(self):
        self.login()
        for changes in [dict(category='invalid'), dict(landmark_id='-1'), dict(review=' '),
                        dict(landmark_id='9' * 30), dict(photo=(io.BytesIO(b'<svg/>'), 'test.png')),
                        dict(photo=(io.BytesIO(b'\x89PNG\r\n\x1a\n' + b'x' * (5 * 1024 * 1024)), 'large.png'))]:
            self.assertEqual(self.save(**changes).status_code, 400)
        self.conn.cursor.assert_not_called()

    def test_save_uses_authenticated_owner_and_authoritative_title(self):
        self.login()
        self.cur.fetchone.return_value = dict(title='Real title', locality_name='Seoul')
        self.assertEqual(self.save().status_code, 200)
        sql, args = self.cur.execute.call_args.args
        self.assertNotIn('ON DUPLICATE KEY UPDATE', sql)
        self.assertEqual(args[-1], date(2026, 1, 1))
        self.assertEqual(args[:5], (7, 'tourism', 4, 'Real title', 'Seoul'))
        self.conn.commit.assert_called_once()

    def test_revisit_requires_own_photo(self):
        self.login()
        self.cur.fetchone.side_effect = [dict(title='Place', locality_name='City'),
                                        dict(photo=b'old-photo', photo_mime='image/png')]
        self.assertEqual(self.save(photo=(io.BytesIO(b''), '')).status_code, 400)
        self.conn.commit.assert_not_called()

    def test_revisit_inserts_two_independent_records(self):
        self.login()
        self.cur.fetchone.return_value = dict(title='Place', locality_name='City')
        self.assertEqual(self.save(review='First visit').status_code, 200)
        self.assertEqual(self.save(review='Second visit', visited_on='2026-02-01').status_code, 200)
        inserts = [call.args for call in self.cur.execute.call_args_list if call.args[0].startswith('INSERT')]
        self.assertEqual(len(inserts), 2)
        self.assertEqual([args[1][5] for args in inserts], ['First visit', 'Second visit'])
        self.assertTrue(all('UPDATE' not in args[0] for args in inserts))

    def test_visit_date_required_valid_and_not_future(self):
        self.login()
        for value in ['', 'invalid', '2026-02-30', '9999-12-31']:
            self.assertEqual(self.save(visited_on=value).status_code, 400)
        self.conn.commit.assert_not_called()

    def test_first_visit_requires_photo_and_existing_place(self):
        self.login()
        self.cur.fetchone.return_value = None
        self.assertEqual(self.save().status_code, 404)
        self.cur.fetchone.side_effect = [dict(title='Place', locality_name='City'), None]
        self.assertEqual(self.save(photo=(io.BytesIO(b''), '')).status_code, 400)
        self.conn.commit.assert_not_called()

    def test_photo_is_private_and_not_cached(self):
        self.login()
        self.cur.fetchone.return_value = dict(photo=b'png-data', photo_mime='image/png')
        result = self.client.get('/api/visits/3/photo')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data, b'png-data')
        self.assertEqual(self.cur.execute.call_args.args[1], (3, 7))
        self.assertEqual(result.headers['Cache-Control'], 'no-store')
        self.assertEqual(result.headers['X-Content-Type-Options'], 'nosniff')
        self.cur.fetchone.return_value = None
        self.assertEqual(self.client.get('/api/visits/3/photo').status_code, 404)

    def test_list_scoped_to_owner_and_includes_category_totals(self):
        self.login()
        self.cur.fetchall.side_effect = [[dict(id=1, category='tourism', landmark_id=4,
            title='Place', locality_name='City', review='Review', updated_at=datetime(2026, 10, 14))],
            [dict(id=4, category='tourism', region_code='47', region_name='경상북도', locality_name='안동시'),
             dict(id=8, category='food', region_code='47', region_name='경상북도', locality_name='안동시'),
             dict(id=9, category='food', region_code='11', region_name='서울특별시', locality_name='중구')]]
        self.cur.fetchone.side_effect = [dict(total=10), dict(total=20), dict(total=30)]
        result = self.client.get('/api/visits')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json['totals'], dict(tourism=10, food=20, event=30))
        self.assertEqual(result.json['visits'][0]['photo_url'], '/api/visits/1/photo')
        self.assertEqual(result.json['visits'][0]['region_name'], '경상북도')
        self.assertEqual(result.json['visits'][0]['locality_name'], '안동시')
        self.assertEqual(result.json['regional_totals'][0]['total'], 2)
        self.assertEqual(result.json['regional_totals'][1]['region_code'], '11')
        query = self.cur.execute.call_args_list[1].args
        self.assertEqual(query[1], (7,))
        self.assertNotIn('photo,', query[0])
        self.assertEqual(result.headers['Cache-Control'], 'no-store')


if __name__ == '__main__':
    unittest.main()
