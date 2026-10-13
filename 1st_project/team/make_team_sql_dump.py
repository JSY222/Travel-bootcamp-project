"""현재 실행 중인 cityname DB를 팀원 배포용 SQL 4개로 완전히 내보냅니다.

실행:  python make_team_sql_dump.py
출력:  team_cityname_sql/01_regions.sql
       team_cityname_sql/02_tourist.sql
       team_cityname_sql/03_food.sql
       team_cityname_sql/04_event.sql

주의: 이 스크립트는 SELECT만 사용하며, 실제 DB를 수정하지 않습니다.
"""
from __future__ import annotations

import os
import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

import pymysql
from pymysql.cursors import DictCursor

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return False

load_dotenv()

DB_NAME = "cityname"
OUT = Path(__file__).resolve().parent / "team_cityname_sql"
REQUIRED = ["regions", "localities", "geo_admin_codes",
            "tourist_landmarks", "food_landmarks", "event_landmarks"]
EXPECTED_COLS = {
    "regions": ["code", "name", "region_type", "display_order"],
    "localities": ["id", "region_code", "name", "locality_type"],
    "geo_admin_codes": ["source_level", "source_code", "locality_id"],
    "tourist_landmarks": ["id", "region_code", "locality_name", "title", "description",
                          "latitude", "longitude", "location_url", "source_name", "locality_id"],
    "food_landmarks": ["id", "region_code", "locality_name", "title", "description",
                       "latitude", "longitude", "location_url", "source_name", "locality_id"],
    "event_landmarks": ["id", "region_code", "locality_name", "title", "description",
                        "latitude", "longitude", "location_url", "source_name", "locality_id"],
}

DDL = {
"regions": """CREATE TABLE `regions` (
  `code` CHAR(2) NOT NULL,
  `name` VARCHAR(50) NOT NULL,
  `region_type` ENUM('province','metro') NOT NULL,
  `display_order` TINYINT UNSIGNED NOT NULL,
  PRIMARY KEY (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;""",
"localities": """CREATE TABLE `localities` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `region_code` CHAR(2) NOT NULL,
  `name` VARCHAR(50) NOT NULL,
  `locality_type` ENUM('city','county','district','town','other') NOT NULL DEFAULT 'other',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_localities_region_name` (`region_code`, `name`),
  UNIQUE KEY `uq_localities_region_id` (`region_code`, `id`),
  CONSTRAINT `fk_localities_region`
    FOREIGN KEY (`region_code`) REFERENCES `regions` (`code`)
    ON UPDATE RESTRICT ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;""",
"geo_admin_codes": """CREATE TABLE `geo_admin_codes` (
  `source_level` ENUM('SIG','EMD') NOT NULL,
  `source_code` VARCHAR(10) NOT NULL,
  `locality_id` INT UNSIGNED NOT NULL,
  PRIMARY KEY (`source_level`, `source_code`),
  KEY `idx_geo_admin_locality` (`locality_id`),
  CONSTRAINT `fk_geo_admin_locality`
    FOREIGN KEY (`locality_id`) REFERENCES `localities` (`id`)
    ON UPDATE RESTRICT ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;""",
}

for short, table in [("tourist", "tourist_landmarks"),
                     ("food", "food_landmarks"), ("event", "event_landmarks")]:
    DDL[table] = f"""CREATE TABLE `{table}` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `region_code` CHAR(2) NOT NULL,
  `locality_name` VARCHAR(50) NOT NULL,
  `title` VARCHAR(120) NOT NULL,
  `description` VARCHAR(255) NOT NULL,
  `latitude` DECIMAL(10,6) NOT NULL,
  `longitude` DECIMAL(10,6) NOT NULL,
  `location_url` VARCHAR(500) NOT NULL,
  `source_name` VARCHAR(100) NOT NULL,
  `locality_id` INT UNSIGNED NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_lookup` (`region_code`, `locality_name`),
  KEY `idx_landmark_locality` (`locality_id`),
  KEY `idx_landmark_region_locality` (`region_code`, `locality_id`),
  CONSTRAINT `fk_{short}_landmarks_region`
    FOREIGN KEY (`region_code`) REFERENCES `regions` (`code`)
    ON UPDATE RESTRICT ON DELETE RESTRICT,
  CONSTRAINT `fk_{short}_region_locality`
    FOREIGN KEY (`region_code`, `locality_id`) REFERENCES `localities` (`region_code`, `id`)
    ON UPDATE RESTRICT ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"""


def sql_literal(value):
    """SQL 모드 NO_BACKSLASH_ESCAPES와 관계없이 안전한 문자열 리터럴."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Decimal):
        return format(value, 'f')
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, bytes):
        return "0x" + value.hex()
    if isinstance(value, (datetime, date, time)):
        value = value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, timedelta):
        value = str(value)
    value = str(value)
    if any((ord(c) < 32 or c == '\\' or ord(c) == 127) for c in value):
        return "CONVERT(0x" + value.encode('utf-8').hex() + " USING utf8mb4)"
    return "'" + value.replace("'", "''") + "'"


def insert_statements(table, rows):
    if not rows:
        return f"-- `{table}`: 0 rows (empty)\n"
    cols = EXPECTED_COLS[table]
    header = "INSERT INTO `" + table + "` (" + ", ".join(f"`{c}`" for c in cols) + ") VALUES\n"
    lines = []
    for start in range(0, len(rows), 70):
        batch = rows[start:start + 70]
        values = ["  (" + ", ".join(sql_literal(row[c]) for c in cols) + ")" for row in batch]
        lines.append(header + ",\n".join(values) + ";\n")
    return "\n".join(lines)


def select_order(table):
    return {
        "regions": "`display_order`, `code`",
        "localities": "`id`",
        "geo_admin_codes": "`source_level`, `source_code`",
        "tourist_landmarks": "`id`",
        "food_landmarks": "`id`",
        "event_landmarks": "`id`",
    }[table]


def read_snapshot(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT table_name AS tname FROM information_schema.tables "
                    "WHERE table_schema=%s AND table_type='BASE TABLE'", (DB_NAME,))
        present = {r['tname'] for r in cur.fetchall()}
        absent = set(REQUIRED) - present
        if absent:
            raise RuntimeError("필수 테이블이 없습니다: " + ", ".join(sorted(absent)))
        for table in REQUIRED:
            cur.execute("SELECT column_name AS cname FROM information_schema.columns "
                        "WHERE table_schema=%s AND table_name=%s",
                        (DB_NAME, table))
            cols = {r['cname'] for r in cur.fetchall()}
            missing = set(EXPECTED_COLS[table]) - cols
            if missing:
                raise RuntimeError(f"{table}에서 컬럼 누락: {sorted(missing)}")
        cur.execute("SELECT table_name AS vname, view_definition AS definition FROM information_schema.views "
                    "WHERE table_schema=%s ORDER BY table_name", (DB_NAME,))
        views = {r['vname']: r['definition'] for r in cur.fetchall()}
        # SELECT 6개 테이블은 하나의 InnoDB 스냅샷에서 읽어 서로 불일치하지 않도록 합니다.
        conn.commit()
        cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        cur.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT")
        snapshot = {}
        for table in REQUIRED:
            cur.execute(f"SELECT {', '.join('`'+c+'`' for c in EXPECTED_COLS[table])} "
                        f"FROM `{table}` ORDER BY {select_order(table)}")
            snapshot[table] = cur.fetchall()
        conn.commit()
    return snapshot, views


def ensure_consistent(data):
    provinces = {str(r['code']) for r in data['regions']}
    localities = {r['id']: r for r in data['localities']}
    for loc in data['localities']:
        if str(loc['region_code']) not in provinces:
            raise RuntimeError(f"localities.id={loc['id']}: 없는 시·도 지역번호")
    for mapping in data['geo_admin_codes']:
        if mapping['locality_id'] not in localities:
            raise RuntimeError("geo_admin_codes에 없는 locality_id가 있습니다")
    for table in REQUIRED[3:]:
        for row in data[table]:
            loc = localities.get(row['locality_id'])
            if loc is None or str(loc['region_code']) != str(row['region_code']):
                raise RuntimeError(f"{table}.id={row['id']}: 지역 외래키 불일치")
    if len(data['regions']) != 17:
        print(f"[주의] regions 개수: {len(data['regions'])} (기존 화면은 17개)")
    if len(data['localities']) != 261 or len(data['geo_admin_codes']) != 282:
        print("[주의] 지역 개수가 화면에서 확인된 261/282와 다릅니다. 실제 DB 상태를 그대로 덤프합니다.")


def order_views(view_defs):
    # VIEW가 다른 VIEW에 의존할 경우 먼저 참조 대상 VIEW를 생성합니다.
    keys = list(view_defs)
    dep = {
        key: {other for other in keys if other != key and re.search(
            rf'(?<![A-Za-z0-9_])`?{re.escape(other)}`?(?![A-Za-z0-9_])',
            view_defs[key], flags=re.I)}
        for key in keys
    }
    ordered = []
    while dep:
        ready = sorted(k for k, refs in dep.items() if not refs)
        if not ready:
            raise RuntimeError("VIEW 간 참조 순서를 결정할 수 없습니다: " + str(dep))
        for k in ready:
            ordered.append(k)
            del dep[k]
        for refs in dep.values():
            refs.difference_update(ready)
    return ordered


def write_files(snapshot, views):
    OUT.mkdir(parents=True, exist_ok=True)
    sqls = {}
    sqls['01_regions.sql'] = [
        "-- 01: GeoJSON 연결 지역 마스터 전체 복원 (시·도 17, localities, 행정코드)\n"
        "-- 완전히 비어 있는 새 DB 전용. 기존 DB에서 실행하면 CREATE TABLE 단계에서 멈춥니다.\n"
        "-- 기존 GeoJSON 강원 원본 코드 51 -> 앱의 regions.code 42 매핑 상태 보존.\n",
        "CREATE DATABASE IF NOT EXISTS `cityname` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n"
        "USE `cityname`;\nSET NAMES utf8mb4;\n"
    ]
    for table in REQUIRED[:3]:
        sqls['01_regions.sql'].append(f"\n-- {table}: {len(snapshot[table])}행\n")
        sqls['01_regions.sql'].append(DDL[table] + "\n\n")
        sqls['01_regions.sql'].append(insert_statements(table, snapshot[table]))
    for filename, table, title in [
        ('02_tourist.sql', 'tourist_landmarks', '관광지'),
        ('03_food.sql', 'food_landmarks', '맛집'),
        ('04_event.sql', 'event_landmarks', '행사'),
    ]:
        sqls[filename] = [
            f"-- {filename}: {title} 테이블 {len(snapshot[table])}행 복원\n",
            "-- 01_regions.sql을 먼저 실행해야 외래키가 정상 생성됩니다.\n",
            "USE `cityname`;\nSET NAMES utf8mb4;\n\n",
            DDL[table] + "\n\n",
            insert_statements(table, snapshot[table])
        ]
    if views:
        sqls['04_event.sql'].append("\n-- 기존 프로젝트 VIEW 복원 (테이블 6개 모두 생성 후 실행)\n")
        for view in order_views(views):
            definition = views[view].strip().rstrip(';')
            sqls['04_event.sql'].append(
                f"CREATE SQL SECURITY INVOKER VIEW `{view}` AS\n{definition};\n\n")
    check = ["\n-- 복원 완료 검증\n"]
    for idx, table in enumerate(REQUIRED):
        p = "SELECT" if idx == 0 else "UNION ALL SELECT"
        check.append(f"{p} '{table}' AS table_name, COUNT(*) AS row_count FROM `{table}`\n")
    check[-1] = check[-1].rstrip() + ";\n"
    sqls['04_event.sql'].append("".join(check))
    for filename, sections in sqls.items():
        (OUT / filename).write_text("".join(sections), encoding='utf-8-sig')
    return sqls


def main():
    conn = pymysql.connect(
        host=os.getenv('DB_HOST', '127.0.0.1'),
        port=int(os.getenv('DB_PORT', '3306')),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', '123'),
        database=DB_NAME,
        charset='utf8mb4',
        cursorclass=DictCursor,
        autocommit=False,
        connect_timeout=10,
    )
    try:
        data, views = read_snapshot(conn)
    finally:
        conn.close()
    ensure_consistent(data)
    expected = {
        "regions": 17, "localities": 261, "geo_admin_codes": 282,
        "tourist_landmarks": 75, "food_landmarks": 44, "event_landmarks": 30,
    }
    for table, n in expected.items():
        if len(data[table]) != n:
            print(f"[참고] {table}: 기존 스크린샷 {n}행 → 현재 {len(data[table])}행 (현재 값으로 생성)")
    write_files(data, views)
    zip_path = OUT.parent / 'cityname_팀원용_SQL_4개.zip'
    with ZipFile(zip_path, 'w', ZIP_DEFLATED) as z:
        for file in ('01_regions.sql', '02_tourist.sql', '03_food.sql', '04_event.sql'):
            z.write(OUT / file, arcname=file)
    print('팀원에게 전달할 ZIP:', zip_path)
    print("\n완료! 생성 위치:", OUT)
    for t in REQUIRED:
        print(f"  {t}: {len(data[t])}행")
    print("  views:", len(views))
    for file in ('01_regions.sql', '02_tourist.sql', '03_food.sql', '04_event.sql'):
        print(' -', OUT / file)
    print('\n팀원은 01 → 02 → 03 → 04 순서로 새 HeidiSQL에서 실행하면 됩니다.')


if __name__ == '__main__':
    main()
