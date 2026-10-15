import unittest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch
from rewards import award_stamp_points, remaining_points, point_history


class RewardTests(unittest.TestCase):
    def award(self, owned, places, existing=False):
        cur = MagicMock()
        cur.fetchone.return_value = {'id': 7}
        cur.fetchall.side_effect = [owned, places]
        cur.rowcount = 0 if existing else 1
        awarded_stamps = []
        with patch('visits.ranking_places', return_value=[]):
            points = award_stamp_points(cur, 7, {'tourism': 'tourist_landmarks'}, awarded_stamps)
        self.assertEqual(sum(stamp['points'] for stamp in awarded_stamps), points)
        if existing:
            self.assertEqual(awarded_stamps, [])
        if points == 10600:
            self.assertEqual([stamp['type'] for stamp in awarded_stamps], ['white', 'silver', 'gold'])
        return points, cur

    def test_complete_city_and_province_awards_all_tiers(self):
        owned = [dict(category='tourism', landmark_id=1)] * 2
        points, cur = self.award(owned, [dict(category='tourism', id=1, region_code='11', locality_name='City')])
        self.assertEqual(points, 10600)
        inserts = [c.args[1] for c in cur.execute.call_args_list if c.args[0].startswith('INSERT')]
        self.assertEqual([row[-1] for row in inserts], [100, 500, 10000])
        self.assertTrue(all(row[0] == 7 for row in inserts))

    def test_incomplete_city_only_awards_white(self):
        points, _ = self.award([dict(category='tourism', landmark_id=1)],
                              [dict(category='tourism', id=i, region_code='11', locality_name='City') for i in [1, 2]])
        self.assertEqual(points, 100)

    def test_existing_awards_are_not_paid_again(self):
        points, _ = self.award([dict(category='tourism', landmark_id=1)],
                              [dict(category='tourism', id=1, region_code='11', locality_name='City')], existing=True)
        self.assertEqual(points, 0)

    def test_no_visits_no_points(self):
        points, _ = self.award([], [])
        self.assertEqual(points, 0)

    def test_decay_boundaries_all_tiers(self):
        start = date(2026, 1, 1)
        for original in [100, 500, 10000]:
            for day, percent in [(0, 100), (14, 100), (15, 90), (18, 60), (22, 20), (23, 10), (400, 10)]:
                with self.subTest(original=original, day=day):
                    expected = 500 if original == 500 else original * percent // 100
                    self.assertEqual(remaining_points(original, start, start + timedelta(days=day)), expected)

    def history(self, dates):
        cur = MagicMock()
        cur.fetchall.side_effect = [
            [dict(stamp_type=kind, stamp_key=key, points=points, created_at=datetime(2026, 1, 1))
             for kind, key, points in [('white', '["tourism", 1]', 100), ('silver', '["11", "City"]', 500), ('gold', '"11"', 10000)]],
            [dict(category='tourism', landmark_id=1, title='Place', locality_name='City', visited_on=day) for day in dates],
            [dict(category='tourism', id=1, title='Place', region_code='11', locality_name='City')],
            [dict(code='11', name='Region')]]
        with patch('visits.ranking_places', return_value=[]):
            return point_history(cur, 7, {'tourism': 'tourist_landmarks'}, today=date(2026, 4, 1))

    def test_revisit_restores_existing_rewards_without_extra_entries(self):
        old = self.history([date(2026, 1, 1)])
        self.assertEqual([row['current_points'] for row in old], [10, 500, 1000])
        restored = self.history([date(2026, 1, 1), date(2026, 3, 31)])
        self.assertEqual([row['current_points'] for row in restored], [100, 500, 10000])
        self.assertEqual(len(restored), 3)

    def test_backdated_review_does_not_replace_later_visit(self):
        history = self.history([date(2026, 3, 31), date(2026, 1, 1)])
        self.assertTrue(all(row['last_visited_on'] == date(2026, 3, 31) for row in history))

    def test_legacy_unknown_visit_uses_award_date(self):
        history = self.history([None])
        self.assertTrue(all(row['last_visited_on'] is None for row in history))
        self.assertEqual([row['current_points'] for row in history], [10, 500, 1000])
