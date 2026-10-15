"""Import task CSV rankings and their enriched original fields without data loss."""
import csv
import io
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import DB_CONFIG
import pymysql
from db.generate_datalab_food_sql import decode_csv, AUDIENCES

DDL = """CREATE TABLE IF NOT EXISTS datalab_food_task_rankings (
 region_code CHAR(2) NOT NULL,
 locality_name VARCHAR(100) NOT NULL,
 period_start CHAR(6) NOT NULL, period_end CHAR(6) NOT NULL,
 audience VARCHAR(10) NOT NULL, poi_id CHAR(32) NOT NULL,
 area_rank INT UNSIGNED NOT NULL, title VARCHAR(255) NOT NULL,
 subtype VARCHAR(100) NOT NULL,
 latitude DECIMAL(12,9) NULL, longitude DECIMAL(12,9) NULL,
 road_address VARCHAR(1000) NOT NULL, parcel_address VARCHAR(1000) NOT NULL,
 phone VARCHAR(255) NOT NULL, source_path VARCHAR(1000) NOT NULL,
 raw_json LONGTEXT NOT NULL,
 PRIMARY KEY (region_code,locality_name,period_start,period_end,audience,poi_id),
 KEY idx_task_rank(region_code,locality_name,audience,area_rank)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"""


def coordinate(value, low, high):
    if not value or not value.strip():
        return None
    number = Decimal(value)
    if not number.is_finite() or not low <= number <= high:
        raise ValueError('Invalid geographic coordinate')
    return number


def collect(root):
    records, duplicates, conflicts, raw_count, excluded = {}, 0, 0, 0, 0
    paths = sorted(root.rglob('*.csv'))
    for path in paths:
        match = re.match(r'^(\d+)_(.+)_(\d{6})-(\d{6})_데이터랩_다운로드', path.parent.name)
        if not match:
            raise ValueError(f'Unknown scope: {path}')
        timestamp, locality, start, end = match.groups()
        locality = locality.replace('+', ' ')
        region = path.relative_to(root).parts[0][:2]
        region = {'51':'42','52':'45'}.get(region,region)
        audience = AUDIENCES[path.stem.rsplit('_',1)[-1]]
        if start > end or any(not 1 <= int(p[4:]) <= 12 for p in [start,end]):
            raise ValueError('Invalid reporting period')
        reader = csv.DictReader(io.StringIO(decode_csv(path.read_bytes())))
        if not {'순위','관광지ID','업소명','분류'}.issubset(reader.fieldnames or []):
            raise ValueError(f'Missing columns: {path}')
        for row in reader:
            raw_count += 1
            poi = row['관광지ID'].strip()
            rank = int(row['순위'])
            if not re.fullmatch('[0-9a-fA-F]{32}',poi) or rank<1 or not row['업소명'].strip():
                raise ValueError(f'Invalid ranking: {path}')
            key = (region,locality,start,end,audience,poi)
            latitude = coordinate(row.get('위도'),-90,90)
            longitude = coordinate(row.get('경도'),-180,180)
            if latitude is None or longitude is None or not (32 <= latitude <= 40 and 124 <= longitude <= 132):
                excluded += 1
                continue
            values = key + (rank,row['업소명'].strip(),row['분류'].strip(),
                latitude,longitude,
                row.get('도로명주소',''),row.get('지번주소',''),row.get('전화번호',''),
                path.relative_to(root).as_posix(),json.dumps(row,ensure_ascii=False))
            if key in records:
                duplicates += 1
                if values[6:14] != records[key][1][6:14]:
                    conflicts += 1
                if timestamp < records[key][0]:
                    continue
            records[key] = (timestamp,values)
    if not records:
        raise ValueError('No CSV data found')
    report = dict(files=len(paths),raw_rows=raw_count,unique_rows=len(records),duplicates=duplicates,
                  changed_copies=conflicts,excluded_no_map=excluded,localities=len({key[:2] for key in records}))
    return [value[1] for value in records.values()],report


def main():
    root = Path(__file__).resolve().parent/'db_test'/'task'
    rows, report = collect(root)
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(DDL)
            cur.execute("ALTER TABLE datalab_food_task_rankings ADD COLUMN IF NOT EXISTS location_url VARCHAR(500) GENERATED ALWAYS AS (CONCAT('https://www.openstreetmap.org/?mlat=',latitude,'&mlon=',longitude,'#map=17/',latitude,'/',longitude)) VIRTUAL")
            cur.execute('SELECT COUNT(*) AS n FROM datalab_food_task_rankings')
            before = cur.fetchone()['n']
            columns = 'region_code,locality_name,period_start,period_end,audience,poi_id,area_rank,title,subtype,latitude,longitude,road_address,parcel_address,phone,source_path,raw_json'
            sql = 'INSERT INTO datalab_food_task_rankings ('+columns+') VALUES ('+','.join(['%s']*16)+') ON DUPLICATE KEY UPDATE '+','.join(f'{name}=VALUES({name})' for name in ['area_rank','title','subtype','latitude','longitude','road_address','parcel_address','phone','source_path','raw_json'])
            for offset in range(0,len(rows),200):
                cur.executemany(sql,rows[offset:offset+200])
            cur.execute('SELECT COUNT(*) AS n FROM datalab_food_task_rankings')
            report.update(added=cur.fetchone()['n']-before)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    out=Path(__file__).resolve().parent/'generated'/'task_csv_import.report.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':
    main()
