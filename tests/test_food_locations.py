import unittest

from food_locations import attach_food_locations


class FoodLocationTests(unittest.TestCase):
    def test_unique_locality_and_title_get_coordinates(self):
        rows = [dict(title='Good Food', locality_name='District')]
        matches = [dict(id=1, title='GoodFood', locality_name='District', latitude='37.5', longitude='127.0', location_url='')]
        attach_food_locations(rows, '11', lambda sql, args: matches)
        self.assertEqual(rows[0]['latitude'], 37.5)
        self.assertEqual(rows[0]['landmark_id'], 1)

    def test_ambiguous_wrong_locality_and_invalid_coordinates_are_not_guessed(self):
        for matches in [[],
            [dict(id=1,title='Food',locality_name='Other',latitude=37,longitude=127,location_url='')],
            [dict(id=i,title='Food',locality_name='District',latitude=37,longitude=127,location_url='') for i in (1,2)],
            [dict(id=1,title='Food',locality_name='District',latitude=0,longitude=0,location_url='')]]:
            rows = [dict(title='Food', locality_name='District')]
            attach_food_locations(rows, '11', lambda sql, args: matches)
            self.assertIsNone(rows[0]['latitude'])
            self.assertIsNone(rows[0]['landmark_id'])


if __name__ == '__main__':
    unittest.main()
