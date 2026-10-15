import csv
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from db.generate_datalab_food_sql import collect, generate, literal


class DataLabSqlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.scope = '11_11110_서울특별시_종로구_202510-202609'
        self.name = '20261014120400_지역_맛집_전체.csv'

    def csv_bytes(self, title="O'Reilly\\맛집", rank=1):
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(['순위', '관광지ID', '업소명', '분류'])
        writer.writerow([rank, 'a' * 32, title, '한식'])
        return out.getvalue().encode('utf-8-sig')

    def put_csv(self, scope=None, raw=None):
        folder = self.root / (scope or self.scope)
        folder.mkdir(exist_ok=True)
        (folder / self.name).write_bytes(raw or self.csv_bytes())

    def test_zip_and_extracted_duplicate_are_collapsed(self):
        self.put_csv()
        self.put_csv(self.scope + ' (2)')
        with zipfile.ZipFile(self.root / (self.scope + '.zip'), 'w') as archive:
            archive.writestr(self.name, self.csv_bytes())
        rows, report = collect(self.root)
        self.assertEqual(len(rows), 1)
        self.assertEqual(report['raw_rows'], 3)
        self.assertEqual(report['duplicate_rows_removed'], 2)

    def test_conflicting_duplicates_abort(self):
        self.put_csv()
        self.put_csv(self.scope + ' (2)', self.csv_bytes(title='Different'))
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            collect(self.root)

    def test_periods_and_all_ranks_preserved(self):
        self.put_csv(raw=self.csv_bytes(rank=21))
        self.put_csv(self.scope.replace('202510-202609', '202507-202606'))
        rows, report = collect(self.root)
        self.assertEqual(len(rows), 2)
        self.assertEqual(report['top20_rows'], 1)
        self.assertEqual(len(report['periods']), 2)

    def test_sql_is_reusable_and_preserves_operational_tables(self):
        self.put_csv()
        output = self.root / 'output' / 'import.sql'
        report = generate(self.root, output)
        sql = output.read_text(encoding='utf-8')
        self.assertIn('ON DUPLICATE KEY UPDATE', sql)
        self.assertIn('START TRANSACTION;', sql)
        self.assertIn('COMMIT;', sql)
        self.assertIn('WHERE area_rank <= 20', sql)
        self.assertNotIn('DELETE FROM', sql)
        self.assertNotIn('DROP TABLE', sql)
        self.assertNotIn('INSERT INTO food_landmarks', sql)
        self.assertEqual(json.loads(output.with_suffix('.report.json').read_text(encoding='utf-8')), report)
        self.assertEqual(literal("a'\\b"), 'CONVERT(0x61275c62 USING utf8mb4)')


if __name__ == '__main__':
    unittest.main()
