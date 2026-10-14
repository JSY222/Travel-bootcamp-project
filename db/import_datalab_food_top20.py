"""Import official Korea Tourism Data Lab restaurant ranking ZIP files.

The script stages and validates every selected locality before replacing data.
Existing food rows are never removed by the default dry-run mode.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import re
import unicodedata
import zipfile
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlencode, unquote
from urllib.request import Request, urlopen

import pymysql
from dotenv import load_dotenv
import os


SOURCE_NAME = "한국관광 데이터랩 지역 맛집 TOP20"
SOURCE_URL = "https://datalab.visitkorea.or.kr/datalab/portal/loc/getAreaDataForm.do#"
TOUR_API_BASE = "https://apis.data.go.kr/B551011/KorService2"
TOURAPI_AREA_BY_REGION = {
    "11": "1", "26": "6", "27": "4", "28": "2", "29": "5", "30": "3",
    "31": "7", "36": "8", "41": "31", "42": "32", "43": "33", "44": "34",
    "45": "37", "46": "38", "47": "35", "48": "36", "50": "39",
}
ZIP_RE = re.compile(r"^\d+_(.+)_(\d{6})-(\d{6})_데이터랩_다운로드\.zip$")
STAGED_ZIP_RE = re.compile(
    r"^(\d{2})_(\d{5})_([^_]+)_([^_]+)_(\d{6})-(\d{6})\.zip$"
)


def csv_text(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    raise ValueError("CSV 문자 인코딩을 확인할 수 없습니다.")


def read_zip(path: Path) -> tuple[str | None, str, str, str, list[dict]]:
    staged_match = STAGED_ZIP_RE.match(path.name)
    if staged_match:
        region_code, _sgg_code, _province, scope, period_start, period_end = staged_match.groups()
    else:
        match = ZIP_RE.match(path.name)
        if not match:
            raise ValueError(f"데이터랩 ZIP 파일명이 아닙니다: {path.name}")
        scope, period_start, period_end = match.groups()
        region_code = None
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.endswith("지역_맛집_전체.csv")]
        if len(names) != 1:
            raise ValueError(f"'지역_맛집_전체.csv'가 정확히 1개여야 합니다: {path.name}")
        reader = csv.DictReader(io.StringIO(csv_text(archive.read(names[0]))))
        rows = []
        for row in reader:
            rank = int(row["순위"])
            if rank > 20:
                continue
            rows.append({
                "rank": rank,
                "poi_id": row["관광지ID"].strip(),
                "title": row["업소명"].strip(),
                "subtype": row["분류"].strip() or None,
            })
    rows.sort(key=lambda item: item["rank"])
    ranks = [row["rank"] for row in rows]
    # 데이터랩 원본에는 공동순위가 있을 수 있습니다(예: 17, 17, 19).
    # 순위를 재계산하지 않고 공식 표기를 그대로 보존하되, 상위 20개 항목인지 검증합니다.
    if len(rows) != 20 or ranks != sorted(ranks) or ranks[0] != 1 or ranks[-1] > 20:
        raise ValueError(f"상위 20개 순위 데이터가 완전하지 않습니다: {path.name} ({ranks})")
    return region_code, scope, period_start, period_end, rows


def normalized_name(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", "", value or ""))
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"\([^)]*\)|\[[^]]*]", "", value)
    return re.sub(r"[^0-9A-Za-z가-힣]", "", value).lower()


def item_list(payload: dict) -> list[dict]:
    response = payload.get("response") or {}
    header = response.get("header") or {}
    result_code = str(header.get("resultCode", ""))
    if result_code not in {"0000", "0"}:
        raise RuntimeError(f"TourAPI 오류 {result_code}: {header.get('resultMsg', '')}")
    items = ((response.get("body") or {}).get("items") or {}).get("item", [])
    if isinstance(items, dict):
        return [items]
    return items or []


class TourApiClient:
    def __init__(self, service_key: str, mobile_app: str, cache_path: Path):
        self.service_key = unquote(service_key.strip())
        self.mobile_app = mobile_app
        self.cache_path = cache_path
        self.cache = {}
        if cache_path.exists():
            self.cache = json.loads(cache_path.read_text(encoding="utf-8"))

    def request(self, endpoint: str, **params) -> dict:
        query = {
            "serviceKey": self.service_key,
            "MobileOS": "ETC",
            "MobileApp": self.mobile_app,
            "_type": "json",
            **params,
        }
        request = Request(
            f"{TOUR_API_BASE}/{endpoint}?{urlencode(query)}",
            headers={"User-Agent": "travel-bootcamp-project/1.0"},
        )
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def sigungu_code(self, region_code: str, locality_name: str) -> tuple[str, str]:
        area_code = TOURAPI_AREA_BY_REGION.get(region_code)
        if not area_code:
            raise ValueError(f"TourAPI 광역코드가 없습니다: {region_code}")
        cache_key = f"sigungu:{area_code}"
        if cache_key not in self.cache:
            self.cache[cache_key] = item_list(self.request(
                "areaCode2", numOfRows=100, pageNo=1, areaCode=area_code
            ))
            self.save()
        # TourAPI는 수원시 장안구 같은 일반구를 수원시 단위로 조회합니다.
        parent_name = locality_name.split()[0]
        wanted = normalized_name(parent_name)
        matches = [
            row for row in self.cache[cache_key]
            if normalized_name(str(row.get("name", ""))) == wanted
        ]
        if len(matches) != 1:
            raise ValueError(f"TourAPI 시군구 코드 연결 실패: {region_code} {locality_name}")
        return area_code, str(matches[0]["code"])

    def restaurants(self, region_code: str, locality_name: str) -> list[dict]:
        cache_key = f"restaurants:{region_code}:{locality_name}"
        if cache_key not in self.cache:
            area_code, sigungu_code = self.sigungu_code(region_code, locality_name)
            rows = item_list(self.request(
                "areaBasedList2", numOfRows=1000, pageNo=1, arrange="A",
                contentTypeId=39, areaCode=area_code, sigunguCode=sigungu_code,
            ))
            words = locality_name.split()
            if len(words) >= 2 and words[-1].endswith("구"):
                district = words[-1]
                rows = [row for row in rows if district in str(row.get("addr1", ""))]
            self.cache[cache_key] = rows
            self.save()
        return self.cache[cache_key]

    def save(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(self.cache, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def best_tourapi_match(
    title: str,
    candidates: list[dict],
    threshold: float,
    exact_only: bool = False,
) -> tuple[dict | None, float]:
    wanted = normalized_name(title)
    exact_matches = [
        candidate
        for candidate in candidates
        if normalized_name(str(candidate.get("title", ""))) == wanted
    ]
    if exact_only:
        # 같은 시군구 안에서도 동명 매장이 둘 이상이면 어느 주소가 맞는지
        # 자동으로 결정하지 않습니다. 정확히 하나일 때만 1:1로 연결합니다.
        if len(exact_matches) == 1:
            return exact_matches[0], 1.0
        return None, 1.0 if exact_matches else 0.0

    scored = []
    for candidate in candidates:
        candidate_name = normalized_name(str(candidate.get("title", "")))
        if not candidate_name:
            continue
        score = 1.0 if candidate_name == wanted else SequenceMatcher(None, wanted, candidate_name).ratio()
        scored.append((score, candidate))
    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored or scored[0][0] < threshold:
        return None, 0.0 if not scored else scored[0][0]
    if len(scored) > 1 and scored[0][0] < 1.0 and scored[0][0] - scored[1][0] < 0.05:
        return None, scored[0][0]
    return scored[0][1], scored[0][0]


def tourapi_fields(match: dict | None, score: float) -> dict:
    if not match:
        return {
            "road_address": None, "latitude": None, "longitude": None, "phone": None,
            "location_url": None, "image_url": None, "tourapi_content_id": None,
            "tourapi_match_score": None, "details_json": None,
        }
    latitude = float(match["mapy"]) if match.get("mapy") else None
    longitude = float(match["mapx"]) if match.get("mapx") else None
    location_url = None
    if latitude is not None and longitude is not None:
        location_url = (
            f"https://www.openstreetmap.org/?mlat={latitude:.8f}&mlon={longitude:.8f}"
            f"#map=16/{latitude:.8f}/{longitude:.8f}"
        )
    details = {
        "tourapi": {
            "content_id": str(match.get("contentid") or ""),
            "content_type_id": str(match.get("contenttypeid") or "39"),
            "category1": match.get("cat1"), "category2": match.get("cat2"),
            "category3": match.get("cat3"), "zipcode": match.get("zipcode"),
            "modified_time": match.get("modifiedtime"), "match_score": round(score, 4),
        }
    }
    return {
        "road_address": " ".join(filter(None, [match.get("addr1"), match.get("addr2")])),
        "latitude": latitude, "longitude": longitude, "phone": match.get("tel") or None,
        "location_url": location_url, "image_url": match.get("firstimage") or None,
        "tourapi_content_id": str(match.get("contentid") or "") or None,
        "tourapi_match_score": round(score, 4),
        "details_json": json.dumps(details, ensure_ascii=False),
    }


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


def resolve_scope(scope: str, localities: list[dict], region_code: str | None = None) -> dict:
    candidates = localities
    if region_code:
        candidates = [row for row in localities if row["region_code"] == region_code]
    exact = [row for row in candidates if row["name"] == scope]
    if len(exact) == 1:
        return exact[0]
    # ZIP 이름에 광역단체명이 함께 들어온 경우 마지막 행정구역 이름으로 재시도합니다.
    short = scope.split()[-1]
    short_matches = [row for row in candidates if row["name"] == short]
    if len(short_matches) == 1:
        return short_matches[0]
    raise ValueError(f"DB 지역과 자동 연결할 수 없습니다: {scope}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_dir", type=Path, help="공식 데이터랩 ZIP이 모인 폴더")
    parser.add_argument("--apply", action="store_true", help="검증 후 실제 교체")
    parser.add_argument("--allow-partial", action="store_true", help="일부 지역만 교체(기본값은 전체 지역 필수)")
    parser.add_argument(
        "--replace-all", action="store_true",
        help="부분 자료라도 기존 맛집 전체를 비우고 수집분만 입력(--allow-partial과 함께 사용)",
    )
    parser.add_argument(
        "--enrich-tourapi", action="store_true",
        help="공공데이터포털 한국관광공사 국문 관광정보 API로 주소·좌표·전화·이미지 보강",
    )
    parser.add_argument(
        "--api-cache", type=Path,
        default=Path(__file__).parent / "data" / "tourapi_food_cache.json",
        help="TourAPI 응답 캐시(JSON)",
    )
    parser.add_argument("--match-threshold", type=float, default=0.92)
    parser.add_argument(
        "--exact-only", action="store_true",
        help="같은 시군구에서 정규화 상호명이 정확히 하나 일치할 때만 1:1로 연결",
    )
    parser.add_argument("--report", type=Path, help="매칭 결과 JSON 보고서 저장 경로")
    parser.add_argument("--missing-report", type=Path, help="아직 ZIP이 없는 지역 JSON 저장 경로")
    args = parser.parse_args()
    if args.replace_all and not args.allow_partial:
        parser.error("--replace-all은 --allow-partial과 함께 사용하세요.")

    zip_paths = sorted(args.zip_dir.glob("*.zip"))
    if not zip_paths:
        raise SystemExit("데이터랩 ZIP 파일이 없습니다.")

    load_dotenv()
    tourapi = None
    if args.enrich_tourapi:
        service_key = os.getenv("TOUR_API_SERVICE_KEY", "").strip()
        if not service_key or service_key.startswith("replace_with_"):
            raise SystemExit("TOUR_API_SERVICE_KEY가 없습니다. 로컬 .env에 인증키를 설정하세요.")
        tourapi = TourApiClient(
            service_key,
            os.getenv("TOUR_API_MOBILE_APP", "travel-bootcamp-project"),
            args.api_cache,
        )

    conn = pymysql.connect(**db_config())
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT l.id, l.region_code, l.name, "
                "GROUP_CONCAT(g.source_code ORDER BY g.source_code) AS source_codes "
                "FROM localities l JOIN geo_admin_codes g ON g.locality_id=l.id "
                "GROUP BY l.id, l.region_code, l.name ORDER BY l.region_code, l.id"
            )
            localities = cur.fetchall()

        staged = []
        report = []
        matched_count = 0
        covered = set()
        for path in zip_paths:
            try:
                region_code, scope, period_start, period_end, rows = read_zip(path)
            except ValueError as exc:
                if "'지역_맛집_전체.csv'" in str(exc):
                    continue
                raise
            locality = resolve_scope(scope, localities, region_code)
            key = (locality["region_code"], locality["name"])
            if key in covered:
                raise ValueError(f"같은 지역 ZIP이 중복되었습니다: {scope}")
            covered.add(key)
            candidates = []
            if tourapi:
                try:
                    candidates = tourapi.restaurants(key[0], key[1])
                except Exception as exc:
                    print(f"경고: TourAPI 조회 실패, 순위만 유지합니다: {key[1]} ({exc})")
            for row in rows:
                match, score = best_tourapi_match(
                    row["title"], candidates, args.match_threshold, args.exact_only
                )
                extra = tourapi_fields(match, score)
                if match:
                    matched_count += 1
                source_key = hashlib.sha256(
                    f"{key[0]}|{key[1]}|{period_start}|{period_end}|{row['poi_id']}".encode("utf-8")
                ).hexdigest()
                staged.append((
                    key[0], key[1], locality["id"], row["title"], row["subtype"],
                    f"{scope} 내비게이션 전체 맛집 {row['rank']}위",
                    extra["road_address"], extra["latitude"], extra["longitude"],
                    extra["phone"], extra["location_url"], extra["image_url"],
                    SOURCE_NAME, SOURCE_URL, 10, source_key, date.today(), date.today(),
                    row["rank"], scope, period_start, period_end, row["poi_id"],
                    extra["tourapi_content_id"], extra["tourapi_match_score"],
                    extra["details_json"],
                ))
                report.append({
                    "region_code": key[0], "locality": key[1], "rank": row["rank"],
                    "datalab_title": row["title"],
                    "tourapi_title": match.get("title") if match else None,
                    "tourapi_content_id": extra["tourapi_content_id"],
                    "match_score": round(score, 4) if score else None,
                    "matched": bool(match),
                })

        expected = {(row["region_code"], row["name"]) for row in localities}
        missing = sorted(expected - covered)
        print(f"미수집 지역: {len(missing)}개")
        if args.missing_report:
            locality_lookup = {(row["region_code"], row["name"]): row for row in localities}
            missing_rows = [{
                "region_code": region_code,
                "locality": name,
                "source_codes": str(locality_lookup[(region_code, name)].get("source_codes") or "").split(","),
            } for region_code, name in missing]
            args.missing_report.parent.mkdir(parents=True, exist_ok=True)
            args.missing_report.write_text(
                json.dumps(missing_rows, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"미수집 보고서: {args.missing_report}")
        if missing and not args.allow_partial:
            sample = ", ".join(name for _, name in missing[:12])
            raise SystemExit(f"전체 교체 중단: {len(missing)}개 지역 ZIP이 없습니다. 예: {sample}")

        print(f"검증 완료: {len(covered)}개 지역, {len(staged)}개 맛집")
        if tourapi:
            print(f"TourAPI 보강: {matched_count}/{len(staged)}개 확정 매칭")
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"매칭 보고서: {args.report}")
        if not args.apply:
            print("DRY RUN: DB를 변경하지 않았습니다. 실제 반영은 --apply를 추가하세요.")
            return

        backup = f"_backup_{date.today():%Y%m%d}_food_landmarks_before_datalab_top20"
        with conn.cursor() as cur:
            cur.execute(f"CREATE TABLE IF NOT EXISTS `{backup}` LIKE food_landmarks")
            cur.execute(f"SELECT COUNT(*) AS n FROM `{backup}`")
            if cur.fetchone()["n"] == 0:
                cur.execute(f"INSERT INTO `{backup}` SELECT * FROM food_landmarks")
            if args.allow_partial and not args.replace_all:
                cur.executemany(
                    "DELETE FROM food_landmarks WHERE region_code=%s AND locality_name=%s",
                    list(covered),
                )
            else:
                cur.execute("DELETE FROM food_landmarks")
            cur.executemany(
                """INSERT INTO food_landmarks (
                    region_code, locality_name, locality_id, title, subtype, description,
                    road_address, latitude, longitude, phone, location_url, image_url,
                    source_name, source_url, source_priority, source_record_key,
                    source_updated_date, last_verified_at, area_rank, ranking_scope,
                    ranking_period_start, ranking_period_end, datalab_poi_id,
                    tourapi_content_id, tourapi_match_score, details_json
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s
                )""",
                staged,
            )
        conn.commit()
        print(f"교체 완료: {len(staged)}개. 백업: {backup}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()

