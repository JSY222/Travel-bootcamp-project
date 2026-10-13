"""Import the EXACT province/SIG/Sejong EMD GeoJSON codes used by map.js.

Requirements: pip install pymysql python-dotenv
Run from Flask project root after 01_migrate_existing_cityname.sql:
    python import_geojson_regions.py

Read local ./static/geo/*.geojson first, otherwise download the same URLs as map.js.
DOES NOT delete existing landmark records or replace their IDs.
"""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

import pymysql
from dotenv import load_dotenv

load_dotenv()

GEO_BASES = [
    "https://cdn.jsdelivr.net/gh/KnellBalm/kr-admin-geojson@main/",
    "https://raw.githubusercontent.com/KnellBalm/kr-admin-geojson/main/",
]
METRO_CODES = {"11", "26", "27", "28", "29", "30", "31", "36"}
# Same administrative-code vintage as the supplied 1013_12sql.txt and map.js.
EXPECTED_PROVINCE_CODES = {
    "11", "26", "27", "28", "29", "30", "31", "36",
    "41", "42", "43", "44", "45", "46", "47", "48", "50",
}

# Compatibility bridge: downloaded GeoJSON uses Gangwon code 51,
# while the existing cityname DB and landmark foreign keys use 42.
# Keep the real SIG_CD/EMD_CD source codes intact in geo_admin_codes.
def db_region_code(source_code):
    code = str(source_code or '')
    return '42' if code == '51' else code



def read_geo(filename):
    local = Path('static') / 'geo' / filename
    if local.is_file():
        print(f'GeoJSON file: {local}')
        with local.open(encoding='utf-8-sig') as f:
            data = json.load(f)
    else:
        data = None
        last_error = None
        for base in GEO_BASES:
            try:
                url = base + filename
                print(f'Downloading {url} ...')
                req = Request(url, headers={'User-Agent': 'Cityname-region-import/1.0'})
                with urlopen(req, timeout=60) as resp:
                    data = json.load(resp)
                break
            except Exception as exc:
                last_error = exc
        if data is None:
            raise RuntimeError(f'Cannot load {filename}: {last_error}')
    if data.get('type') != 'FeatureCollection' or not isinstance(data.get('features'), list):
        raise ValueError(f'Invalid GeoJSON feature collection: {filename}')
    return data['features']


def app_locality_name(props, metro):
    """Exactly mirrors cityGroupName() in the current map.js."""
    name = props.get('SIG_KOR_NM')
    if metro:
        return name
    words = (props.get('FULL_NM') or '').split()
    if (len(words) >= 3 and words[1].endswith('시')
            and words[2].endswith('구')):
        return words[1]
    return name


def locality_type(name, metro=False, sejong=False):
    if sejong:
        return 'town'
    if name.endswith('시'):
        return 'city'
    if name.endswith('군'):
        return 'county'
    if name.endswith('구'):
        return 'district'
    return 'other'


def main():
    ctprvn = read_geo('ctprvn.geojson')
    sig = read_geo('sig.geojson')
    emd = read_geo('emd.geojson')  # For Sejong's eup/myeon/dong selection.

    province_rows = []
    for feature in ctprvn:
        p = feature['properties']
        code, name = db_region_code(p.get('CTPRVN_CD')), p.get('CTP_KOR_NM')
        if code and name:
            province_rows.append((code, name))
    found = {code for code, _ in province_rows}
    if len(found) != len(province_rows):
        raise ValueError('Duplicate province code after GeoJSON-to-DB normalization.')
    if found != EXPECTED_PROVINCE_CODES:
        raise ValueError(
            f'GeoJSON province codes (after 51→42 normalization) differ from the DB snapshot. '
            f'Missing={sorted(EXPECTED_PROVINCE_CODES - found)}, '
            f'Unexpected={sorted(found - EXPECTED_PROVINCE_CODES)}. '
            f'Confirm the source version before importing.'
        )

    # Each map selection locality has a synthetic numeric ID. It may have multiple SIG_CD.
    locality_rows = {}
    source_rows = []
    for feature in sig:
        p = feature['properties']
        region_code = db_region_code(p.get('CTPRVN_CD'))
        sig_code = str(p.get('SIG_CD') or '')
        if region_code == '36':  # Display Sejong at EMD level instead.
            continue
        name = app_locality_name(p, region_code in METRO_CODES)
        if region_code not in found or not sig_code or not name:
            continue
        locality_rows[(region_code, name)] = locality_type(name, region_code in METRO_CODES)
        source_rows.append(('SIG', sig_code, region_code, name))

    for feature in emd:
        p = feature['properties']
        if str(p.get('CTPRVN_CD') or '') != '36':
            continue
        code, name = str(p.get('EMD_CD') or ''), p.get('EMD_KOR_NM')
        if code and name:
            locality_rows[('36', name)] = 'town'
            source_rows.append(('EMD', code, '36', name))

    connection = pymysql.connect(
        host=os.getenv('DB_HOST', '127.0.0.1'),
        port=int(os.getenv('DB_PORT', '3306')),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', '123'),
        database='cityname',
        charset='utf8mb4',
        autocommit=False,
    )
    try:
        with connection.cursor() as cur:
            # Missing province masters only; keep existing DB names/order intact.
            cur.executemany(
                "INSERT INTO regions(code,name,region_type,display_order) "
                "VALUES(%s,%s,%s,%s) "
                "ON DUPLICATE KEY UPDATE code=VALUES(code)",
                [(code, name, 'metro' if code in METRO_CODES else 'province', i + 1)
                 for i, (code, name) in enumerate(province_rows)],
            )
            cur.executemany(
                "INSERT INTO localities(region_code,name,locality_type) "
                "VALUES(%s,%s,%s) "
                "ON DUPLICATE KEY UPDATE locality_type=VALUES(locality_type)",
                [(region, name, kind) for (region, name), kind in locality_rows.items()],
            )
            cur.execute("SELECT id, region_code, name FROM localities")
            lookup = {(region_code, name): loc_id for loc_id, region_code, name in cur.fetchall()}

            mappings = [(level, code, lookup[(region, name)])
                        for level, code, region, name in source_rows]
            cur.executemany(
                "INSERT INTO geo_admin_codes(source_level,source_code,locality_id) "
                "VALUES(%s,%s,%s) "
                "ON DUPLICATE KEY UPDATE locality_id=VALUES(locality_id)",
                mappings,
            )
        connection.commit()
        print(f'Imported {len(province_rows)} provinces; '
              f'{len(locality_rows)} GeoJSON locality groups; '
              f'{len(mappings)} SIG/EMD code mappings.')
        print('Existing tourism/food/event rows were preserved.')
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == '__main__':
    main()
