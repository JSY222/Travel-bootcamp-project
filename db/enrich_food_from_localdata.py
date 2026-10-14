"""Enrich DataLab restaurant rankings from the official LOCALDATA CSV.

Only an active restaurant whose normalized business name is unique inside the
same province and municipality is accepted.  EPSG:5174 coordinates from the
source file are converted to WGS84 without an external GIS dependency.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

import pymysql
from dotenv import load_dotenv


REGION_ALIASES = {
    "11": ("서울특별시", "서울시"),
    "26": ("부산광역시", "부산시"),
    "27": ("대구광역시", "대구시"),
    "28": ("인천광역시", "인천시"),
    "29": ("광주광역시", "광주시"),
    "30": ("대전광역시", "대전시"),
    "31": ("울산광역시", "울산시"),
    "36": ("세종특별자치시", "세종시"),
    "41": ("경기도",),
    "42": ("강원특별자치도", "강원도"),
    "43": ("충청북도", "충북"),
    "44": ("충청남도", "충남"),
    "45": ("전북특별자치도", "전라북도", "전북"),
    "46": ("전라남도", "전남"),
    "47": ("경상북도", "경북"),
    "48": ("경상남도", "경남"),
    "50": ("제주특별자치도", "제주도"),
}


def normalized_name(value: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]+", "", (value or "").casefold())


def db_config() -> dict:
    load_dotenv()
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", "123"),
        "database": "cityname",
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": False,
    }


def _meridional_arc(phi: float, a: float, e2: float) -> float:
    e4 = e2 * e2
    e6 = e4 * e2
    return a * (
        (1 - e2 / 4 - 3 * e4 / 64 - 5 * e6 / 256) * phi
        - (3 * e2 / 8 + 3 * e4 / 32 + 45 * e6 / 1024) * math.sin(2 * phi)
        + (15 * e4 / 256 + 45 * e6 / 1024) * math.sin(4 * phi)
        - (35 * e6 / 3072) * math.sin(6 * phi)
    )


def epsg5174_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """Convert Korean 1985 / Modified Central Belt to WGS84."""
    a = 6377397.155
    flattening = 1 / 299.1528128
    e2 = flattening * (2 - flattening)
    ep2 = e2 / (1 - e2)
    lat0 = math.radians(38)
    lon0 = math.radians(127.002890277778)
    m = _meridional_arc(lat0, a, e2) + (northing - 500000)
    mu = m / (a * (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256))
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    fp = (
        mu
        + (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu)
        + (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu)
        + (151 * e1**3 / 96) * math.sin(6 * mu)
        + (1097 * e1**4 / 512) * math.sin(8 * mu)
    )
    sin_fp, cos_fp, tan_fp = math.sin(fp), math.cos(fp), math.tan(fp)
    n1 = a / math.sqrt(1 - e2 * sin_fp**2)
    r1 = a * (1 - e2) / (1 - e2 * sin_fp**2) ** 1.5
    t1 = tan_fp**2
    c1 = ep2 * cos_fp**2
    d = (easting - 200000) / n1
    lat = fp - (n1 * tan_fp / r1) * (
        d**2 / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1**2 - 9 * ep2) * d**4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1**2 - 252 * ep2 - 3 * c1**2)
        * d**6
        / 720
    )
    lon = lon0 + (
        d
        - (1 + 2 * t1 + c1) * d**3 / 6
        + (5 - 2 * c1 + 28 * t1 - 3 * c1**2 + 8 * ep2 + 24 * t1**2)
        * d**5
        / 120
    ) / cos_fp

    # Seven-parameter transformation published with EPSG:5174.
    n = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    x = n * math.cos(lat) * math.cos(lon)
    y = n * math.cos(lat) * math.sin(lon)
    z = n * (1 - e2) * math.sin(lat)
    dx, dy, dz = -145.907, 505.034, 685.756
    rx, ry, rz = (-1.162, 2.347, 1.592)
    arcsec = math.pi / (180 * 3600)
    rx, ry, rz = rx * arcsec, ry * arcsec, rz * arcsec
    scale = 1 + 6.342e-6
    x2 = dx + scale * x - rz * y + ry * z
    y2 = dy + rz * x + scale * y - rx * z
    z2 = dz - ry * x + rx * y + scale * z

    wgs_a = 6378137.0
    wgs_f = 1 / 298.257223563
    wgs_e2 = wgs_f * (2 - wgs_f)
    p = math.hypot(x2, y2)
    wgs_lat = math.atan2(z2, p * (1 - wgs_e2))
    for _ in range(8):
        wgs_n = wgs_a / math.sqrt(1 - wgs_e2 * math.sin(wgs_lat) ** 2)
        wgs_lat = math.atan2(z2 + wgs_e2 * wgs_n * math.sin(wgs_lat), p)
    return math.degrees(wgs_lat), math.degrees(math.atan2(y2, x2))


def locality_matches(address: str, region_code: str, locality_name: str) -> bool:
    aliases = REGION_ALIASES.get(region_code, ())
    return locality_name in address and (not aliases or any(alias in address for alias in aliases))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--encoding", default="cp949")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    conn = pymysql.connect(**db_config())
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, region_code, locality_name, title, details_json "
                "FROM food_landmarks ORDER BY id"
            )
            food_rows = cur.fetchall()

        targets: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
        name_index: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
        for row in food_rows:
            key = (row["region_code"], row["locality_name"], normalized_name(row["title"]))
            targets[key].append(row)
            if key not in name_index[key[2]]:
                name_index[key[2]].append(key)

        candidates: dict[tuple[str, str, str], dict[tuple, dict]] = defaultdict(dict)
        scanned = 0
        active_name_hits = 0
        with args.csv_path.open(encoding=args.encoding, newline="", errors="replace") as source:
            reader = csv.DictReader(source)
            required = {"사업장명", "영업상태명", "도로명주소", "지번주소", "좌표정보(X)", "좌표정보(Y)"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"필수 CSV 열이 없습니다: {sorted(missing)}")
            for source_row in reader:
                scanned += 1
                if source_row.get("영업상태명") != "영업/정상":
                    continue
                norm = normalized_name(source_row.get("사업장명", ""))
                possible_keys = name_index.get(norm)
                if not possible_keys:
                    continue
                active_name_hits += 1
                address = (source_row.get("도로명주소") or source_row.get("지번주소") or "").strip()
                if not address:
                    continue
                try:
                    x = float((source_row.get("좌표정보(X)") or "").strip())
                    y = float((source_row.get("좌표정보(Y)") or "").strip())
                    latitude, longitude = epsg5174_to_wgs84(x, y)
                except (TypeError, ValueError):
                    continue
                if not (32 <= latitude <= 40 and 124 <= longitude <= 132):
                    continue
                for key in possible_keys:
                    if not locality_matches(address, key[0], key[1]):
                        continue
                    identity = (
                        source_row.get("관리번호") or "",
                        address,
                        round(latitude, 7),
                        round(longitude, 7),
                    )
                    candidates[key][identity] = {
                        "business_name": source_row.get("사업장명"),
                        "management_number": source_row.get("관리번호"),
                        "road_address": address,
                        "parcel_address": (source_row.get("지번주소") or "").strip() or None,
                        "latitude": round(latitude, 8),
                        "longitude": round(longitude, 8),
                        "phone": (source_row.get("전화번호") or "").strip() or None,
                        "business_type": (source_row.get("업태구분명") or "").strip() or None,
                        "last_modified": (source_row.get("최종수정시점") or "").strip() or None,
                    }

        updates = []
        report_rows = []
        ambiguous_source = 0
        duplicate_target = 0
        for key, rows in targets.items():
            matches = list(candidates.get(key, {}).values())
            reason = None
            if len(rows) != 1:
                reason = "duplicate_target_name"
                duplicate_target += len(rows)
            elif len(matches) == 0:
                reason = "no_unique_localdata_match"
            elif len(matches) > 1:
                reason = "ambiguous_localdata_match"
                ambiguous_source += 1
            else:
                match = matches[0]
                row = rows[0]
                try:
                    details = json.loads(row.get("details_json") or "{}")
                except (TypeError, json.JSONDecodeError):
                    details = {}
                details["localdata"] = {
                    "management_number": match["management_number"],
                    "parcel_address": match["parcel_address"],
                    "business_type": match["business_type"],
                    "last_modified": match["last_modified"],
                    "coordinate_system": "EPSG:5174 converted to EPSG:4326",
                    "matching_rule": "unique exact normalized name within province and municipality",
                }
                updates.append((
                    match["road_address"], match["latitude"], match["longitude"],
                    match["phone"],
                    f"https://www.openstreetmap.org/?mlat={match['latitude']:.8f}"
                    f"&mlon={match['longitude']:.8f}#map=17/{match['latitude']:.8f}/{match['longitude']:.8f}",
                    date.today(), json.dumps(details, ensure_ascii=False), row["id"],
                ))
            for row in rows:
                report_rows.append({
                    "id": row["id"], "region_code": key[0], "locality": key[1],
                    "title": row["title"], "candidate_count": len(matches),
                    "matched": len(rows) == 1 and len(matches) == 1,
                    "reason": reason,
                    "match": matches[0] if len(rows) == 1 and len(matches) == 1 else None,
                })

        summary = {
            "source_file": str(args.csv_path),
            "source_rows_scanned": scanned,
            "current_food_rows": len(food_rows),
            "active_exact_name_hits_before_region_filter": active_name_hits,
            "matched_unique": len(updates),
            "unmatched": len(food_rows) - len(updates),
            "ambiguous_source_keys": ambiguous_source,
            "duplicate_target_rows": duplicate_target,
            "applied": bool(args.apply),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(
                json.dumps({"summary": summary, "rows": report_rows}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"보고서: {args.report}")
        if not args.apply:
            print("DRY RUN: DB를 변경하지 않았습니다.")
            return

        backup = f"_backup_{date.today():%Y%m%d}_food_before_localdata_enrichment"
        with conn.cursor() as cur:
            cur.execute(f"CREATE TABLE IF NOT EXISTS `{backup}` LIKE food_landmarks")
            cur.execute(f"SELECT COUNT(*) AS n FROM `{backup}`")
            if cur.fetchone()["n"] == 0:
                cur.execute(f"INSERT INTO `{backup}` SELECT * FROM food_landmarks")
            cur.executemany(
                "UPDATE food_landmarks SET road_address=%s, latitude=%s, longitude=%s, "
                "phone=COALESCE(%s, phone), location_url=%s, last_verified_at=%s, details_json=%s "
                "WHERE id=%s",
                updates,
            )
        conn.commit()
        print(f"DB 반영 완료: {len(updates)}건, 백업: {backup}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
