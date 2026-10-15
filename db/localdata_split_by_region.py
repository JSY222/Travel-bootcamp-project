"""식품_일반음식점.csv 를 개방자치단체코드별로 나눠 task/{광역}/{시군구}/ 에 넣고,
데이터랩 지역맛집 폴더를 대응하는 시군구 폴더로 복사한다.

폴더 이름은 static/images/regions/manifest.csv 의 경로 규칙을 따른다.
예: 11_seoul/11_jongno-gu/식품_일반음식점_3000000.csv

사용법:
    python3 -I db/localdata_split_by_region.py <식품_일반음식점.csv> <지역 폴더> \
        <region_map.json> <regions manifest.csv> <task 폴더>
region_map.json 은 localdata_region_map.py 의 출력이다. 원본은 수정하지 않는다.
"""

from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

csv.field_size_limit(10**9)

# 2026-07 인천 행정구역 개편으로 사라진 옛 구 폴더: (폴더명 일부) -> (대표 코드, 매칭에 쓸 코드들)
OVERRIDES = {
    "동구_202507-202606": ("3501000", ["3501000"]),
    "서구_202507-202606": ("3561000", ["3561000", "3565000"]),
    "중구_202507-202606": ("3491000", ["3491000", "3501000"]),
    "제주특별자치도_202510-202609": ("6510000", ["6510000", "6520000"]),
}


def region_paths(manifest_csv: Path) -> dict[tuple[str, str], str]:
    """(상위 시도명, 시군구명) -> 'xx_sido/xx_sigungu' (regions 이미지 폴더 규칙)."""
    paths: dict[tuple[str, str], str] = {}
    with manifest_csv.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            rel = Path(row["path"])
            if row["level"] == "시·도":
                paths[(row["name_ko"], "")] = rel.parent.as_posix()
            else:
                paths[(row["parent_ko"], row["name_ko"])] = rel.with_suffix("").as_posix()
    return paths


def locate(paths: dict[tuple[str, str], str], sido: str, sigungu: str) -> str:
    if sigungu.startswith("세종"):
        sido_dir = paths[(sido, "")]
        return f"{sido_dir}/{sido_dir}"
    # 전남광주통합특별시의 시군구는 regions 에서 옛 광주광역시/전라남도 아래에 있다.
    parents = ["광주광역시", "전라남도"] if sido == "전남광주통합특별시" else [sido]
    for parent in parents:
        if (parent, sigungu) in paths:
            return paths[(parent, sigungu)]
    raise KeyError((sido, sigungu))


def main() -> None:
    source, folders_dir, map_json, regions_manifest, task = (Path(a) for a in sys.argv[1:6])
    data = json.loads(map_json.read_text(encoding="utf-8"))
    codes = data["codes"]

    task.mkdir(parents=True, exist_ok=True)
    paths = region_paths(regions_manifest)
    region_dir: dict[str, Path] = {}
    for code, meta in sorted(codes.items()):
        region_dir[code] = task / locate(paths, meta["sido"], meta["sigungu"])
        region_dir[code].mkdir(parents=True, exist_ok=True)

    # 1) 지역맛집 폴더를 코드 폴더로 복사
    manifest, warnings = [], []
    for item in data["folders"]:
        override = next((v for k, v in OVERRIDES.items() if k in item["folder"]), None)
        if override:
            home, pool = override
        else:
            cands = item["candidates"]
            seen, uniq = set(), []
            for c in cands:  # 세종처럼 후보가 중복되는 경우 제거
                if c["code"] not in seen:
                    seen.add(c["code"])
                    uniq.append(c)
            top = uniq[0]
            home, pool = top["code"], [top["code"]]
            second = uniq[1]["hits"] if len(uniq) > 1 else -1
            if top["hits"] < 5 or (len(uniq) > 1 and top["hits"] - second < 5):
                warnings.append((item["folder"], [(c["code"], c["hits"]) for c in uniq[:3]]))
        dest = region_dir[home] / item["folder"]
        if not dest.exists():
            shutil.copytree(folders_dir / item["folder"], dest)
        manifest.append({
            "region_folder": region_dir[home].relative_to(task).as_posix(),
            "ranking_folder": item["folder"],
            "home_code": home,
            "pool_codes": pool,
            "gu": item["gu"],
        })

    # 2) 식품_일반음식점.csv 를 코드별로 분할 (UTF-8 BOM, 열 구성은 원본과 동일)
    handles, writers, counts = {}, {}, {}
    with source.open(encoding="cp949", newline="", errors="replace") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        for code, d in region_dir.items():
            out = (d / f"식품_일반음식점_{code}.csv").open("w", encoding="utf-8-sig", newline="")
            handles[code] = out
            writers[code] = csv.writer(out)
            writers[code].writerow(header)
            counts[code] = 0
        for row in reader:
            code = row[0]
            writers[code].writerow(row)
            counts[code] += 1
    for h in handles.values():
        h.close()

    regions = {
        code: {
            "folder": region_dir[code].relative_to(task).as_posix(),
            "sido": codes[code]["sido"],
            "sigungu": codes[code]["sigungu"],
            "source_file": f"식품_일반음식점_{code}.csv",
            "rows": counts[code],
        }
        for code in region_dir
    }
    (task / "_manifest.json").write_text(
        json.dumps({"regions": regions, "rankings": manifest}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"지역 폴더 {len(region_dir)}개, 랭킹 폴더 복사 {len(manifest)}개, 분할 행 {sum(counts.values())}")
    for folder, c in warnings:
        print("확인 필요:", folder, c)


if __name__ == "__main__":
    main()
