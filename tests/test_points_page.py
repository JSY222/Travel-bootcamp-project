import unittest
from unittest.mock import MagicMock, patch
from flask import render_template
from app import app


class PointsPageTests(unittest.TestCase):
    def test_template_without_search_context(self):
        with app.test_request_context('/points'):
            html = render_template('points.html', history=[], member_points=0)
        self.assertIn('name="start"', html)
        self.assertIn('id="pointRegion"', html)
        self.assertIn('id="pointLocality"', html)

    def test_route_passes_search_context(self):
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value.fetchall.return_value = []
        with app.test_client() as client:
            with client.session_transaction() as session:
                session.update(member_id=7, member_name='Test')
            with patch('app.pymysql.connect', return_value=conn), patch('rewards.point_history', return_value=[]):
                response = client.get('/points?start=2026-01-01&region=11')
        self.assertEqual(response.status_code, 200)
        self.assertIn('value="2026-01-01"', response.get_data(as_text=True))
