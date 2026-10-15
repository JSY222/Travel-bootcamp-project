import unittest
from recommendations import rank_places


class RecommendationTests(unittest.TestCase):
    def place(self, i, text):
        return dict(id=i, category='tourism', title=text, description=None)

    def test_returns_fifteen_even_when_keywords_sparse(self):
        results = rank_places([self.place(i, '장소') for i in range(30)], 'INFP', ['힐링/자연'])
        self.assertEqual(len(results), 15)
        self.assertTrue(all(p['match_level'] == '탐색 추천' for p in results))

    def test_style_changes_order_and_explanations(self):
        places = [self.place(1, '숲 자연 산책'), self.place(2, '역사 문화 박물관')]
        nature = rank_places(places, 'ISTJ', ['힐링/자연'])
        culture = rank_places(places, 'ISTJ', ['역사/문화'])
        self.assertEqual(nature[0]['id'], 1)
        self.assertEqual(culture[0]['id'], 2)
        self.assertIn('힐링/자연', nature[0]['reason'])

    def test_each_mbti_axis_contributes_and_score_capped(self):
        result = rank_places([self.place(1, '숲 산책 미술 갤러리 감성 사진 카페 골목')], 'INFP', ['힐링/자연'])[0]
        self.assertEqual(result['mbti_score'], 40)
        self.assertLessEqual(result['score'], 100)
        for letter in 'INFP':
            self.assertIn(letter+' ', result['reason'])

    def test_no_duplicates_and_small_dataset(self):
        place = self.place(1, '숲')
        self.assertEqual(len(rank_places([place, place], 'INFP', [])), 1)
