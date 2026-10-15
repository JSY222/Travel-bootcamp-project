"""지역(데이터랩 맛집 랭킹) 폴더를 LOCALDATA 개방자치단체코드에 연결한다.

폴더명에는 시도가 없어 '중구'처럼 이름이 겹치므로, 랭킹의 업소명이 각 후보 코드의
영업 중인 사업장명과 몇 개나 일치하는지로 코드를 고른다.

사용법: python3 -I db/localdata_region_map.py <식품_일반음식점.csv> <지역 폴더> <출력 json>
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(10**9)

PERIOD = re.compile(r"_\d{6}-\d{6}_데이터랩_다운로드$")


def norm(value: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]+", "", (value or "").casefold())


def split_address(address: str) -> tuple[str, str, str]:
    """주소에서 (시도, 시군구, 구) 를 뽑는다. 구는 '시 아래 구'일 때만 채운다."""
    tok = address.split()
    if len(tok) < 2:
        return "", "", ""
    sido = tok[0]
    if sido.startswith("세종"):
        return sido, sido, ""
    sigungu = tok[1]
    gu = ""
    if sigungu.endswith("시") and len(tok) > 2 and tok[2].endswith("구"):
        gu = tok[2]
    return sido, sigungu, gu


def load_source(path: Path):
    """코드별 요약과 (코드, 구) 별 영업 중 사업장명 집합을 만든다."""
    info: dict[str, dict] = {}
    active: dict[tuple[str, str], set[str]] = defaultdict(set)
    sido_cnt: dict[str, Counter] = defaultdict(Counter)
    sgg_cnt: dict[str, Counter] = defaultdict(Counter)
    total: Counter = Counter()
    with path.open(encoding="cp949", newline="", errors="replace") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            code = row["개방자치단체코드"]
            total[code] += 1
            address = (row.get("지번주소") or row.get("도로명주소") or "").strip()
            sido, sgg, gu = split_address(address)
            if sido:
                sido_cnt[code][sido] += 1
                sgg_cnt[code][sgg] += 1
            if row.get("영업상태명") == "영업/정상":
                name = norm(row.get("사업장명", ""))
                if name:
                    active[(code, "")].add(name)
                    if gu:
                        active[(code, gu)].add(name)
    for code, n in total.items():
        info[code] = {
            "rows": n,
            "sido": sido_cnt[code].most_common(1)[0][0] if sido_cnt[code] else "",
            "sigungu": sgg_cnt[code].most_common(1)[0][0] if sgg_cnt[code] else "",
        }
    return info, active


def parse_folder(name: str) -> tuple[str, str]:
    """폴더명에서 (시군구, 구) 를 뽑는다. '수원시+영통구' -> ('수원시', '영통구')."""
    body = PERIOD.sub("", re.sub(r"^\d+_", "", name))
    if "+" in body:
        base, gu = body.split("+", 1)
        return base, gu
    return body, ""


def ranking_names(folder: Path) -> list[str]:
    names: list[str] = []
    for path in sorted(folder.glob("*.csv")):
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                names.append(norm(row.get("업소명", "")))
    return [n for n in names if n]


def main() -> None:
    source, folders_dir, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    info, active = load_source(source)

    by_sgg: dict[str, list[str]] = defaultdict(list)
    for code, meta in info.items():
        by_sgg[meta["sigungu"]].append(code)
        if meta["sido"].startswith(("제주", "세종")):
            by_sgg[meta["sido"]].append(code)

    result = []
    for folder in sorted(p for p in folders_dir.iterdir() if p.is_dir()):
        base, gu = parse_folder(folder.name)
        names = ranking_names(folder)
        candidates = by_sgg.get(base, [])
        scored = []
        for code in candidates:
            pool = active.get((code, gu), set())
            hit = sum(1 for n in names if n in pool)
            scored.append((hit, code))
        scored.sort(reverse=True)
        result.append({
            "folder": folder.name,
            "base": base,
            "gu": gu,
            "ranking_rows": len(names),
            "candidates": [
                {"code": c, "sido": info[c]["sido"], "sigungu": info[c]["sigungu"], "hits": h}
                for h, c in scored
            ],
        })
    out.write_text(json.dumps({"codes": info, "folders": result}, ensure_ascii=False, indent=1))
    print(f"codes={len(info)} folders={len(result)} -> {out}")


if __name__ == "__main__":
    main()
