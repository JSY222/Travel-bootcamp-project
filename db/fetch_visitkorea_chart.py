"""대한민국 구석구석 '음식점 검색 순위'(area_chart.do) 데이터를 지역별로 받아 캐시한다.

페이지가 쓰는 /call (cmd=AREA_CHART_SGG_INFO, AREA_CHART_LIST) 응답에서 업소명, 도로명주소, 좌표, 분류를
가져온다. 시군구마다 현지인/외지인 x (전체, 한식, 외국식, 카페&베이커리, 기타) 호출로 상위 10위씩 받는다.
요청은 순차로 천천히 보내고, 응답은 캐시 파일에 저장해 다시 실행해도 같은 요청을 반복하지 않는다.

사용법: python3 -I db/fetch_visitkorea_chart.py <task 폴더> [--delay 0.5] [--limit N]
결과: <task 폴더>/_visitkorea_chart.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

URL = "https://korean.visitkorea.or.kr/call"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (travel-bootcamp student project; low-rate fetch)",
    "X-Requested-With": "XMLHttpRequest",
}
SIDOS = [
    "서울특별시", "부산광역시", "대구광역시", "인천광역시", "대전광역시", "울산광역시",
    "세종특별자치시", "경기도", "강원특별자치도", "충청북도", "충청남도", "전북특별자치도",
    "전남광주통합특별시", "경상북도", "경상남도", "제주특별자치도",
]
CATEGORIES = {"all": [], "korean": ["korean"], "country": ["country"], "bakery": ["bakery"], "etc": ["etc"]}


def call(**params) -> dict:
    data = urllib.parse.urlencode(params).encode()
    last: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(URL, data=data, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.load(resp)
            if body.get("header", {}).get("process") != "success":
                raise RuntimeError(f"응답 실패: {body.get('header')}")
            return body["body"]
        except (urllib.error.URLError, RuntimeError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"3회 실패: {params.get('cmd')} {last}")


def region_codes(sgg_list: list[dict], sido: str, sigungu: str) -> list[str]:
    """우리 시군구명을 구석구석 시군구 코드들로 바꾼다. '수원시'는 '수원시 영통구' 등을 모두 포함한다."""
    return [
        x["SGG_CD"] for x in sgg_list
        if x["CTPV_NM"] == sido and (x["SGG_NM"] == sigungu or x["SGG_NM"].startswith(sigungu + " "))
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("task", type=Path)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--limit", type=int, default=0, help="처리할 시군구 코드 수 제한(시험용)")
    args = parser.parse_args()

    out = args.task / "_visitkorea_chart.json"
    cache = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    cache.setdefault("sgg_list", [])
    cache.setdefault("charts", {})
    manifest = json.loads((args.task / "_manifest.json").read_text(encoding="utf-8"))

    def save() -> None:
        out.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    if not cache["sgg_list"]:
        for sido in SIDOS:
            cache["sgg_list"].extend(call(cmd="AREA_CHART_SGG_INFO", ctpvNm=sido, sggNmList="[]")["sggList"])
            time.sleep(args.delay)
        save()

    regions: dict[str, list[str]] = {}
    for code, meta in manifest["regions"].items():
        # 전남광주통합특별시 안의 광주/전남은 구석구석 목록에서도 같은 시도 이름 아래에 있다.
        regions[code] = region_codes(cache["sgg_list"], meta["sido"], meta["sigungu"])
    cache["regions"] = regions
    missing = [c for c, v in regions.items() if not v]
    if missing:
        print("구석구석 코드를 못 찾은 지역:", [(c, manifest["regions"][c]["folder"]) for c in missing])

    needed = sorted({cd for v in regions.values() for cd in v})
    if args.limit:
        needed = needed[: args.limit]
    sido_of = {x["SGG_CD"]: x["CTPV_NM"] for x in cache["sgg_list"]}
    total = len(needed) * len(CATEGORIES) * 2
    done = 0
    print(f"시군구 코드 {len(needed)}개, 호출 예정 {total}회 (캐시 제외 전)")
    for cd in needed:
        entry = cache["charts"].setdefault(cd, {})
        for cname, cl in CATEGORIES.items():
            for kind in (1, 2):
                key = f"{cname}:{kind}"
                done += 1
                if key in entry:
                    continue
                body = call(cmd="AREA_CHART_LIST", ctpvNm=sido_of[cd], sggCds=json.dumps([cd]),
                            categories=json.dumps(cl), type=kind)
                entry[key] = [
                    {
                        "name": e.get("ENT_NM1"), "addr": e.get("ROAD_NM_ADDR"), "lat": e.get("LAT"),
                        "lon": e.get("LON"), "category": e.get("SE_CD"), "url": e.get("INFO_URL_ADDR"),
                    }
                    for e in body.get("chartList", [])
                ]
                time.sleep(args.delay)
        save()
        print(f"[{done}/{total}] {cd}", flush=True)
    save()
    print("완료:", out)


if __name__ == "__main__":
    sys.exit(main())
