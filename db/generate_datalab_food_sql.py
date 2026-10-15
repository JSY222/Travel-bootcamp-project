"""Generate offline MariaDB ranking import SQL; never connects to a database."""
import argparse
import csv
import io
import json
import re
import zipfile
from collections import Counter
from pathlib import Path

SCOPE = re.compile(r'^(\d{2})_(\d{5})_([^_]+)_(.+)_(\d{6})-(\d{6})(?: \(\d+\))?$')
AUDIENCES = {'전체': 'all', '현지인': 'local', '외지인': 'nonlocal'}
DDL = """CREATE TABLE IF NOT EXISTS datalab_food_rankings (
  region_code CHAR(2) NOT NULL,
  sigungu_code CHAR(5) NOT NULL,
  province_name VARCHAR(50) NOT NULL,
  locality_name VARCHAR(100) NOT NULL,
  period_start CHAR(6) NOT NULL,
  period_end CHAR(6) NOT NULL,
  audience ENUM('all','local','nonlocal') NOT NULL,
  poi_id CHAR(32) NOT NULL,
  area_rank SMALLINT UNSIGNED NOT NULL,
  title VARCHAR(255) NOT NULL,
  subtype VARCHAR(100) NOT NULL,
  PRIMARY KEY (sigungu_code,period_start,period_end,audience,poi_id),
  KEY idx_datalab_food_rank (region_code,locality_name,audience,area_rank)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


def decode_csv(raw):
    for encoding in ('utf-8-sig', 'cp949', 'euc-kr'):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    raise ValueError('Unsupported CSV encoding')


def literal(value):
    if isinstance(value, int):
        return str(value)
    # Hex UTF-8 literals work with both default and NO_BACKSLASH_ESCAPES modes.
    return "CONVERT(0x" + value.encode('utf-8').hex() + " USING utf8mb4)" if value else "''"


def collect(root):
    records = {}
    file_count = 0
    raw_rows = 0
    duplicates = 0

    def ingest(scope_name, filename, raw):
        nonlocal file_count, raw_rows, duplicates
        audience_name = Path(filename).stem.rsplit('_', 1)[-1]
        if audience_name not in AUDIENCES:
            raise ValueError(f'Unknown ranking audience: {filename}')
        match = SCOPE.fullmatch(scope_name)
        if not match:
            raise ValueError(f'Unrecognized locality/period filename: {scope_name}')
        region, sigungu, province, locality, start, end = match.groups()
        if not sigungu.startswith(region) or start > end or any(not 1 <= int(value[4:]) <= 12 for value in (start, end)):
            raise ValueError(f'Invalid locality/period: {scope_name}')
        reader = csv.DictReader(io.StringIO(decode_csv(raw)))
        if not {'순위', '관광지ID', '업소명', '분류'}.issubset(reader.fieldnames or []):
            raise ValueError(f'Missing ranking columns: {filename}')
        file_count += 1
        file_keys = set()
        for item in reader:
            if not any(item.values()):
                continue
            rank = int(item['순위'])
            poi = item['관광지ID'].strip().lower()
            title = item['업소명'].strip()
            subtype = item['분류'].strip()
            if not re.fullmatch('[0-9a-f]{32}', poi) or not 1 <= rank <= 65535 or not title or len(title) > 255 or len(subtype) > 100:
                raise ValueError(f'Invalid ranking record: {scope_name}/{filename}: {item!r}')
            row = (region, sigungu, province, locality, start, end, AUDIENCES[audience_name], poi, rank, title, subtype)
            key = (sigungu, start, end, AUDIENCES[audience_name], poi)
            if key in file_keys:
                raise ValueError(f'Duplicate POI within source: {scope_name}/{filename}: {poi}')
            file_keys.add(key)
            raw_rows += 1
            if key in records:
                if records[key] != row:
                    raise ValueError(f'Conflicting source copies: {scope_name}/{filename}: {poi}')
                duplicates += 1
            else:
                records[key] = row

    for archive_path in sorted(root.rglob('*.zip')):
        with zipfile.ZipFile(archive_path) as archive:
            for name in sorted(archive.namelist()):
                if name.lower().endswith('.csv') and not name.startswith('__MACOSX/'):
                    ingest(archive_path.stem, name, archive.read(name))
    for path in sorted(root.rglob('*.csv')):
        ingest(path.parent.name, path.name, path.read_bytes())
    if not records:
        raise ValueError('No ranking records found')
    rows = sorted(records.values(), key=lambda row: (row[1], row[4], row[5], row[6], row[8], row[7]))
    report = dict(source_files=file_count, raw_rows=raw_rows, duplicate_rows_removed=duplicates,
                  unique_rows=len(rows), top20_rows=sum(row[8] <= 20 for row in rows),
                  localities=len({row[1] for row in rows}),
                  audiences=dict(Counter(row[6] for row in rows)),
                  periods=sorted({f'{row[4]}-{row[5]}' for row in rows}))
    return rows, report


def generate(root, output):
    rows, report = collect(root)
    columns = 'region_code,sigungu_code,province_name,locality_name,period_start,period_end,audience,poi_id,area_rank,title,subtype'
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8', newline='\n') as sql:
        sql.write('-- Generated offline from checked-in DataLab CSV/ZIP files.\n')
        sql.write('-- Ranking import only: no guessed coordinates, no DELETE/DROP, no changes to food_landmarks.\n')
        sql.write('-- Source duplicates are collapsed; conflicting copies abort generation.\n')
        sql.write('-- ' + json.dumps(report, ensure_ascii=False) + '\n')
        sql.write('SET NAMES utf8mb4;\nUSE cityname;\n' + DDL)
        sql.write('START TRANSACTION;\n')
        for offset in range(0, len(rows), 100):
            sql.write(f'INSERT INTO datalab_food_rankings ({columns}) VALUES\n')
            sql.write(',\n'.join('(' + ','.join(literal(value) for value in row) + ')' for row in rows[offset:offset + 100]))
            sql.write('\nON DUPLICATE KEY UPDATE province_name=VALUES(province_name),locality_name=VALUES(locality_name),'
                      'area_rank=VALUES(area_rank),title=VALUES(title),subtype=VALUES(subtype);\n')
        sql.write('COMMIT;\n')
        sql.write('CREATE OR REPLACE VIEW v_datalab_food_top20 AS SELECT * FROM datalab_food_rankings WHERE area_rank <= 20;\n')
        sql.write('SELECT audience,COUNT(*) AS row_count FROM datalab_food_rankings GROUP BY audience;\n')
        sql.write('SELECT audience,COUNT(*) AS top20_count FROM v_datalab_food_top20 GROUP BY audience;\n')
    output.with_suffix('.report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).parent / 'data' / 'datalab_food_top20')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent / 'generated' / 'datalab_food_rankings.sql')
    args = parser.parse_args()
    print(json.dumps(generate(args.source, args.output), ensure_ascii=True))
