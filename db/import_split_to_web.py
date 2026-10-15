"""Import split-format tourism/events into the existing web tables, preserving IDs."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pymysql
from app import DB_CONFIG

ROOT = Path(__file__).resolve().parent / 'cityname_split'
REGIONS = {'경상북도':'47','경상남도':'48','전북특별자치도':'45','전라북도':'45',
           '전라남도':'46','제주특별자치도':'50','강원특별자치도':'42','강원도':'42',
           '충청북도':'43','충청남도':'44','경기도':'41','서울특별시':'11',
           '대구광역시':'27','부산광역시':'26','광주광역시':'29','인천광역시':'28',
           '대전광역시':'30','울산광역시':'31','세종특별자치시':'36'}


def load_raw(cur, path, wanted):
    """Read generated INSERT blocks, keeping semicolons inside strings intact."""
    pending = []
    created = set()
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if not pending:
            match = re.match(r'INSERT INTO `([^`]+)` \((.*?)\) VALUES', line)
            if not match or match[1] not in wanted:
                continue
            table = match[1]
            if table not in created:
                columns = re.findall(r'`([^`]+)`', match[2])
                cur.execute('CREATE TEMPORARY TABLE `raw_' + table + '` (' +
                            ','.join('`'+c+'` LONGTEXT NULL' for c in columns) + ')')
                created.add(table)
            line = line.replace('INSERT INTO `'+table+'`', 'INSERT INTO `raw_'+table+'`', 1)
        pending.append(line)
        if line.rstrip().endswith(';'):
            cur.execute('\n'.join(pending))
            pending = []
    if pending:
        raise ValueError('Incomplete INSERT block')


def main():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            # Existing event rows are preserved; source events may have no coordinates.
            cur.execute('ALTER TABLE event_landmarks MODIFY latitude DECIMAL(10,6) NULL, MODIFY longitude DECIMAL(10,6) NULL')
            cur.execute('ALTER TABLE tourist_landmarks MODIFY latitude DECIMAL(10,6) NULL, MODIFY longitude DECIMAL(10,6) NULL')
            load_raw(cur, ROOT/'01_지역_출처.sql', {'regions','administrative_divisions','data_sources'})
            cur.execute('SELECT * FROM raw_regions')
            region_ids = {r['id']: REGIONS.get(r['name']) for r in cur.fetchall()}
            cur.execute('SELECT * FROM raw_administrative_divisions')
            divisions = {r['id']: r['name'] for r in cur.fetchall()}
            cur.execute('SELECT * FROM raw_data_sources')
            sources = {r['id']: r['name'] for r in cur.fetchall()}
            cur.execute('SELECT code FROM regions')
            available = {r['code'] for r in cur.fetchall()}
            cur.execute('SELECT id,region_code,name FROM localities')
            localities = {(r['region_code'],r['name']):r['id'] for r in cur.fetchall()}
            for filename, raw, target in [('02_관광지.sql','tourist_attractions','tourist_landmarks'),('03_행사.sql','events','event_landmarks')]:
                load_raw(cur, ROOT/filename, {raw})
                cur.execute('SELECT * FROM raw_'+raw)
                rows = cur.fetchall()
                cur.execute('SELECT region_code,locality_name,title,description FROM '+target)
                existing = set()
                legacy = set()
                for r in cur.fetchall():
                    name = re.sub(r'\s+', '', r['title'])
                    period = r['description'].split(' | ')[0] if r['description'].startswith('기간:') else ''
                    existing.add((r['region_code'],r['locality_name'],name,period if raw=='events' else ''))
                    if not period:
                        legacy.add((r['region_code'],r['locality_name'],name))
                added = duplicate = skipped = 0
                for row in rows:
                    code = region_ids.get(row['region_id'])
                    locality = divisions.get(row['division_id'])
                    if not locality:
                        address = row['road_address'] or row['parcel_address'] or ''
                        match = re.search(r'\S+[시군구](?=\s|$)', address.split(' ',1)[-1])
                        locality = match[0] if match else None
                    if code not in available or not locality:
                        skipped += 1
                        continue
                    period = f'기간: {row["start_date"] or "미정"} ~ {row["end_date"] or "미정"}' if raw=='events' else ''
                    title = row['name'][:120]
                    key = (code,locality,re.sub(r'\s+','',title),period)
                    if key in existing or key[:3] in legacy:
                        duplicate += 1
                        continue
                    if (code,locality) not in localities:
                        kind = 'city' if locality.endswith('시') else 'county' if locality.endswith('군') else 'district' if locality.endswith('구') else 'other'
                        cur.execute('INSERT INTO localities (region_code,name,locality_type) VALUES (%s,%s,%s)',(code,locality,kind))
                        localities[(code,locality)] = cur.lastrowid
                    description = ' | '.join(v for v in [period, row['road_address'] or row['parcel_address'], row['subtype'], row['summary']] if v)[:255]
                    lat, lng = row['latitude'], row['longitude']
                    url = row['website_url'] or (f'https://www.openstreetmap.org/?mlat={lat}&mlon={lng}#map=17/{lat}/{lng}' if lat and lng else '')
                    cur.execute(f'INSERT INTO {target} (region_code,locality_name,title,description,latitude,longitude,location_url,source_name,locality_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                                (code,locality,title,description,lat,lng,url[:500],sources.get(row['source_id'],'공공데이터')[:100],localities[(code,locality)]))
                    existing.add(key)
                    added += 1
                print(f'{target}: source={len(rows)}, added={added}, duplicate={duplicate}, skipped={skipped}',flush=True)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
