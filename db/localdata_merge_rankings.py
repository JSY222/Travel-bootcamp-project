"""데이터랩 지역맛집 CSV 뒤에 LOCALDATA 식품_일반음식점 정보를 이름으로 매칭해 붙인다.

task/{코드}_{시도}_{시군구}/ 안의 *_지역_맛집_*.csv, *_지역맛집_*.csv (복사본)을 제자리에서 고친다.
원본 열(순위, 관광지ID, 업소명, 분류)은 그대로 두고 오른쪽에 열을 추가하며, 다시 실행해도 같은 결과가 나온다.

매칭 규칙 (정규화 = 소문자화, (주)·[한식] 꼬리표 제거, 한글/영숫자만 남김)
  정확       업소명과 사업장명이 정규화 후 같고, 영업/정상 인 후보가 하나
  정확(중복)  같은 조건의 영업/정상 후보가 둘 이상 -> 채우지 않고 후보 관리번호만 기록
  정확(폐업) 이름은 같지만 영업/정상 후보가 없음 -> 채우지 않음
  부분       정확 일치가 없고, 한쪽 이름이 다른 쪽에 포함(4자 이상, 긴 이름의 50% 이상)되는
             영업/정상 후보가 하나
  부분(중복)  위와 같되 후보가 둘 이상 -> 채우지 않음
  구석구석    위 방법으로 채우지 못한 행 중, 같은 지역의 대한민국 구석구석 '음식점 검색 순위'
             (db/fetch_visitkorea_chart.py 로 받은 _visitkorea_chart.json)에 업소명이 정규화 후
             같고 주소가 하나로 정해지면 그 업소명·분류·도로명주소·좌표를 채움 (관리번호 없음)
  부분(충돌)  부분 일치 후보가 다른 업소명의 정확 일치와 같은 가게이거나, 서로 다른 업소명 둘
             이상의 부분 일치와 같은 가게 (예: '나주곰탕거리' 와 '나주곰탕노안집' 이 모두 '나주곰탕')
             -> 채우지 않고 관리번호만 후보관리번호에 기록
  없음       후보 없음

사용법: python3 -I db/localdata_merge_rankings.py <task 폴더> <코드> [<코드> ...]
"""

from __future__ import annotations

import csv
import importlib.util
import json
import re
import sys
from pathlib import Path

csv.field_size_limit(10**9)

ACTIVE = "영업/정상"
ADDED = [
    "매칭구분", "매칭후보수", "관리번호", "사업장명", "영업상태명", "업태구분명", "인허가일자",
    "도로명주소", "지번주소", "전화번호", "좌표정보(X)", "좌표정보(Y)", "위도", "경도", "후보관리번호",
]
BASE_COLS = 4  # 순위, 관광지ID, 업소명, 분류
MIN_PARTIAL = 4
MIN_COVER = 0.5  # 부분 일치에서 짧은 이름이 긴 이름의 몇 % 이상이어야 하는지
CORP_MARK = re.compile(r"\((?:주|유|사|재|합|농|영)\)|㈜|㈔")
BRACKET_TAG = re.compile(r"\[[^\]]*\]")


def _load_converter():
    path = Path(__file__).with_name("enrich_food_from_localdata.py")
    spec = importlib.util.spec_from_file_location("enrich_food_from_localdata", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.epsg5174_to_wgs84


def norm(value: str) -> str:
    """대소문자·기호·법인 표기((주) 등)·'[한식]' 같은 분류 꼬리표를 지운 비교용 이름."""
    text = BRACKET_TAG.sub("", CORP_MARK.sub("", value or ""))
    return re.sub(r"[^0-9a-z가-힣]+", "", text.casefold())


def gu_of(row: dict) -> str:
    tok = (row.get("지번주소") or row.get("도로명주소") or "").split()
    if len(tok) > 2 and tok[1].endswith("시") and tok[2].endswith("구"):
        return tok[2]
    return ""


def load_pool(task: Path, regions: dict, codes: list[str], gu: str) -> list[dict]:
    rows: list[dict] = []
    for code in codes:
        meta = regions[code]
        path = task / meta["folder"] / meta["source_file"]
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                if gu and gu_of(row) != gu:
                    continue
                rows.append(row)
    return rows


class Matcher:
    def __init__(self, rows: list[dict], to_wgs84, chart: dict[str, list[dict]] | None = None):
        self.to_wgs84 = to_wgs84
        self.chart = chart or {}
        self.by_name: dict[str, list[dict]] = {}
        for row in rows:
            key = norm(row.get("사업장명", ""))
            if key:
                self.by_name.setdefault(key, []).append(row)
        self.active_names = [
            (k, [r for r in v if r.get("영업상태명") == ACTIVE])
            for k, v in self.by_name.items()
        ]
        self.active_names = [(k, v) for k, v in self.active_names if v]
        self.cache: dict[str, list[str]] = {}

    def lookup(self, name: str) -> list[str]:
        key = norm(name)
        if key in self.cache:
            return self.cache[key]
        result = self._lookup(key)
        self.cache[key] = result
        return result

    def settle(self, names: set[str]) -> None:
        """같은 가게에 여러 업소명이 붙은 부분 일치를 '부분(충돌)'로 낮춘다."""
        claims: dict[str, list[tuple[str, str]]] = {}
        for name in names:
            result = self.lookup(name)
            if result[0] in ("정확", "부분"):
                claims.setdefault(result[2], []).append((result[0], norm(name)))
        for record_id, items in claims.items():
            partial = {key for kind, key in items if kind == "부분"}
            exact = {key for kind, key in items if kind == "정확"}
            if partial and (exact or len(partial) > 1):
                for key in partial:
                    self.cache[key] = ["부분(충돌)", "1"] + [""] * (len(ADDED) - 3) + [record_id]

    def supplement(self, names: set[str]) -> None:
        """LOCALDATA 로 못 채운 행을 구석구석 순위 데이터의 같은 이름으로 채운다."""
        for name in names:
            key = norm(name)
            result = self.lookup(name)
            if result[0] in ("정확", "부분") or key not in self.chart:
                continue
            found = self.chart[key]
            if len({e["addr"] for e in found}) != 1:
                continue
            e = found[0]
            self.cache[key] = [
                "구석구석", "1", "", e["name"] or "", "", e["category"] or "", "", e["addr"] or "",
                "", "", "", "", e["lat"] or "", e["lon"] or "", result[-1],
            ]

    def _lookup(self, key: str) -> list[str]:
        empty = [""] * (len(ADDED) - 3)
        if not key:
            return ["없음", "0"] + empty + [""]
        exact = self.by_name.get(key, [])
        active = [r for r in exact if r.get("영업상태명") == ACTIVE]
        if len(active) == 1:
            return self._filled("정확", 1, active[0])
        if len(active) > 1:
            return ["정확(중복)", str(len(active))] + empty + [self._ids(active)]
        if exact:
            return ["정확(폐업)", str(len(exact))] + empty + [self._ids(exact)]
        partial: list[dict] = []
        for other, rows in self.active_names:
            short, long_ = sorted((key, other), key=len)
            if len(short) >= MIN_PARTIAL and short in long_ and len(short) / len(long_) >= MIN_COVER:
                partial.extend(rows)
        if len(partial) == 1:
            return self._filled("부분", 1, partial[0])
        if len(partial) > 1:
            return ["부분(중복)", str(len(partial))] + empty + [self._ids(partial)]
        return ["없음", "0"] + empty + [""]

    @staticmethod
    def _ids(rows: list[dict]) -> str:
        return "|".join(r.get("관리번호", "") for r in rows[:5])

    def _filled(self, kind: str, count: int, row: dict) -> list[str]:
        x = (row.get("좌표정보(X)") or "").strip()
        y = (row.get("좌표정보(Y)") or "").strip()
        lat = lon = ""
        try:
            la, lo = self.to_wgs84(float(x), float(y))
            if 32 <= la <= 40 and 124 <= lo <= 132:
                lat, lon = f"{la:.8f}", f"{lo:.8f}"
        except (TypeError, ValueError):
            pass
        return [
            kind, str(count), row.get("관리번호", ""), row.get("사업장명", ""),
            row.get("영업상태명", ""), row.get("업태구분명", ""), row.get("인허가일자", ""),
            (row.get("도로명주소") or "").strip(), (row.get("지번주소") or "").strip(),
            (row.get("전화번호") or "").strip(), x, y, lat, lon, "",
        ]


def load_chart(task: Path, manifest: dict, pool_codes: list[str], gu: str) -> dict[str, list[dict]]:
    """구석구석 순위 데이터를 정규화한 업소명 -> 항목 목록으로 만든다 (파일이 없으면 빈 사전)."""
    path = task / "_visitkorea_chart.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    chart: dict[str, list[dict]] = {}
    seen: set[tuple[str, str]] = set()
    for code in pool_codes:
        for sgg in data.get("regions", {}).get(code, []):
            for items in data["charts"].get(sgg, {}).values():
                for e in items:
                    key = norm(e["name"])
                    if not key or (gu and gu not in (e["addr"] or "")) or (key, e["addr"]) in seen:
                        continue
                    seen.add((key, e["addr"]))
                    chart.setdefault(key, []).append(e)
    return chart


def merge_region(task: Path, manifest: dict, code: str, to_wgs84) -> dict:
    regions = manifest["regions"]
    folder = task / regions[code]["folder"]
    report = {"region": regions[code]["folder"], "files": []}
    pools: dict[tuple, Matcher] = {}
    entries = [e for e in manifest["rankings"] if e["home_code"] == code]
    names_by_pool: dict[tuple, set[str]] = {}
    for entry in entries:
        key = (tuple(entry["pool_codes"]), entry["gu"])
        if key not in pools:
            rows = load_pool(task, regions, entry["pool_codes"], entry["gu"])
            pools[key] = Matcher(rows, to_wgs84, load_chart(task, manifest, entry["pool_codes"], entry["gu"]))
        names = names_by_pool.setdefault(key, set())
        for path in (folder / entry["ranking_folder"]).glob("*.csv"):
            with path.open(encoding="utf-8-sig", newline="") as fh:
                names.update(row[2] for row in list(csv.reader(fh))[1:] if len(row) > 2)
    for key, matcher in pools.items():
        matcher.settle(names_by_pool[key])
        matcher.supplement(names_by_pool[key])
    for entry in entries:
        matcher = pools[(tuple(entry["pool_codes"]), entry["gu"])]
        for path in sorted((folder / entry["ranking_folder"]).glob("*.csv")):
            with path.open(encoding="utf-8-sig", newline="") as fh:
                source = [row[:BASE_COLS] for row in csv.reader(fh)]
            header, body = source[0], source[1:]
            out = [header + ADDED]
            counts: dict[str, int] = {}
            for row in body:
                row = row + [""] * (BASE_COLS - len(row))
                added = matcher.lookup(row[2])
                counts[added[0]] = counts.get(added[0], 0) + 1
                out.append(row + added)
            with path.open("w", encoding="utf-8-sig", newline="") as fh:
                csv.writer(fh).writerows(out)
            report["files"].append({
                "ranking_folder": entry["ranking_folder"], "file": path.name,
                "rows": len(body), "pool_rows": sum(len(v) for v in matcher.by_name.values()),
                "counts": counts,
            })
    (folder / "_merge_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return report


def main() -> None:
    task = Path(sys.argv[1])
    manifest = json.loads((task / "_manifest.json").read_text(encoding="utf-8"))
    to_wgs84 = _load_converter()
    for code in sys.argv[2:]:
        report = merge_region(task, manifest, code, to_wgs84)
        total = sum(f["rows"] for f in report["files"])
        agg: dict[str, int] = {}
        for f in report["files"]:
            for k, v in f["counts"].items():
                agg[k] = agg.get(k, 0) + v
        print(code, report["region"], total, agg)


if __name__ == "__main__":
    main()
