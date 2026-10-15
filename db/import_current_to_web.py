"""Import current SQL value blocks into web tables without replacing existing IDs."""
import re
import sys
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pymysql
from app import DB_CONFIG

COLUMNS = ['region_code','locality_name','title','description','latitude','longitude','location_url','source_name']


def identity(row, kind):
    key = (row['region_code'], row['locality_name'], re.sub(r'\s+', '', row['title']))
    if kind == 'food':
        return key + tuple(Decimal(str(row[c])).quantize(Decimal('.0001'), rounding=ROUND_HALF_UP) if row[c] is not None else None for c in ['latitude','longitude'])
    if kind == 'event':
        return key + (row['description'].split(' | ')[0] if row['description'].startswith('기간:') else '',)
    return key


def main():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute('ALTER TABLE tourist_landmarks MODIFY latitude DECIMAL(10,6) NULL, MODIFY longitude DECIMAL(10,6) NULL')
            cur.execute('ALTER TABLE event_landmarks MODIFY latitude DECIMAL(10,6) NULL, MODIFY longitude DECIMAL(10,6) NULL')
            cur.execute('SELECT code FROM regions')
            regions = {row['code'] for row in cur.fetchall()}
            cur.execute('SELECT id,region_code,name FROM localities')
            localities = {(row['region_code'],row['name']):row['id'] for row in cur.fetchall()}
            root = Path(__file__).resolve().parent/'current'
            for kind, filename, target in [('tourism','04_tourist_landmarks_temp.sql','tourist_landmarks'),('food','05_food_landmarks_temp.sql','food_landmarks'),('event','06_event_landmarks_temp.sql','event_landmarks')]:
                cur.execute('CREATE TEMPORARY TABLE incoming_places (region_code CHAR(2),locality_name VARCHAR(50),title VARCHAR(120),description VARCHAR(255),latitude DECIMAL(11,8) NULL,longitude DECIMAL(11,8) NULL,location_url VARCHAR(500),source_name VARCHAR(100))')
                pending = []
                for line in (root/filename).read_text(encoding='utf-8-sig').splitlines():
                    if not pending:
                        match = re.match(r'INSERT INTO `\w+`\s*\((.*?)\) VALUES',line)
                        if not match or [c.strip().strip('`') for c in match[1].split(',')] != COLUMNS:
                            continue
                        line = re.sub(r'^INSERT INTO `\w+`','INSERT INTO incoming_places',line)
                    pending.append(line)
                    if line.rstrip().endswith(';'):
                        cur.execute('\n'.join(pending))
                        pending=[]
                if pending:
                    raise RuntimeError('Incomplete SQL value block')
                cur.execute('SELECT * FROM incoming_places')
                rows=cur.fetchall()
                cur.execute('SELECT '+','.join(COLUMNS)+' FROM '+target)
                previous=cur.fetchall()
                existing={identity(row,kind) for row in previous}
                examples={identity(row,'tourism') for row in previous if row['source_name']=='프로젝트 예제 / OSM 위치 지도'}
                batch=[]
                duplicate=skipped=0
                for row in rows:
                    if row['region_code']=='51' and '51' not in regions:row['region_code']='42'
                    if row['region_code']=='52' and '52' not in regions:row['region_code']='45'
                    key=identity(row,kind)
                    if key in existing or identity(row,'tourism') in examples:
                        duplicate+=1
                        continue
                    if row['region_code'] not in regions or not row['locality_name'] or not row['title']:
                        skipped+=1
                        continue
                    locality_key=(row['region_code'],row['locality_name'])
                    if locality_key not in localities:
                        name=row['locality_name']
                        unit='city' if name.endswith('시') else 'county' if name.endswith('군') else 'district' if name.endswith('구') else 'other'
                        cur.execute('INSERT INTO localities (region_code,name,locality_type) VALUES (%s,%s,%s)',(*locality_key,unit))
                        localities[locality_key]=cur.lastrowid
                    batch.append(tuple(row[c] for c in COLUMNS)+(localities[locality_key],))
                    existing.add(key)
                sql=f'INSERT INTO {target} ('+','.join(COLUMNS)+',locality_id) VALUES ('+','.join(['%s']*9)+')'
                for i in range(0,len(batch),250):cur.executemany(sql,batch[i:i+250])
                print(f'{target}: source={len(rows)}, added={len(batch)}, duplicate={duplicate}, skipped={skipped}',flush=True)
                cur.execute('DROP TEMPORARY TABLE incoming_places')
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__=='__main__':
    main()
