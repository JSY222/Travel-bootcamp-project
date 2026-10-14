# 한국관광 데이터랩 지역 맛집 TOP20 원본

한국관광 데이터랩의 공식 `데이터 다운로드` 기능으로 받은 지역별 ZIP을 보관합니다.

- 기준: 전체 맛집 순위 1~20위
- 기간: 2025-10 ~ 2026-09
- 파일명: `{광역코드}_{시군구코드}_{광역시도}_{시군구}_{기간}.zip`
- 원본 ZIP 내부의 `지역_맛집_전체.csv`만 가져오며, 화면 표를 별도로 수집하지 않습니다.
- 동명이 시군구의 오연결을 막기 위해 광역시도와 행정코드를 파일명에 함께 기록합니다.
- 전체 지역 검증이 끝나기 전에는 기존 `food_landmarks` 데이터를 교체하지 않습니다.

## 공공데이터포털 보강

`db/import_datalab_food_top20.py`는 데이터랩 순위를 기준 데이터로 유지하면서
한국관광공사 국문 관광정보 서비스의 음식점(`contentTypeId=39`)을 이름으로 연결합니다.
확실하게 일치한 항목만 주소, 좌표, 전화번호, 대표 이미지와 TourAPI 콘텐츠 ID를 추가합니다.

1. 공공데이터포털에서 `한국관광공사_국문 관광정보 서비스_GW` 활용신청
2. `.env.example`을 참고해 로컬 `.env`에 `TOUR_API_SERVICE_KEY` 설정
3. 실제 변경 전 검증 및 매칭 보고서 생성

```text
python db/import_datalab_food_top20.py db/data/datalab_food_top20 \
  --allow-partial --enrich-tourapi --exact-only \
  --report db/data/tourapi_match_report.json
```

검증 결과를 확인한 다음에만 `--apply`를 추가합니다. API 응답은
`db/data/tourapi_food_cache.json`에 저장해 같은 지역을 반복 호출하지 않습니다.
`--exact-only`를 사용하면 같은 시군구 안에서 정규화한 상호명이 정확히 하나만
일치하는 경우에만 주소와 좌표를 저장합니다. 동명 매장이 여러 개이거나 이름이
일치하지 않는 항목은 잘못된 주소를 넣지 않고 빈 값으로 남깁니다.

공식 파일이 없는 지역은 비워 두고 현재 확보분만 운영 DB에 남길 경우:

```text
python db/import_datalab_food_top20.py db/data/datalab_food_top20 \
  --allow-partial --replace-all --apply
```

## API 승인 전 LOCALDATA 파일로 주소·좌표 보강

공공데이터포털의 `전국일반음식점표준데이터` CSV를 받은 뒤 아래처럼 먼저
DRY RUN 보고서를 생성합니다. 같은 광역지역·시군구 안에서 영업 중인 업소의
정규화 상호명이 정확히 하나 일치하고 좌표가 있는 경우만 연결됩니다.

```text
python db/enrich_food_from_localdata.py "다운로드한 CSV 경로" \
  --report work/localdata_food_match_report.json
```

보고서를 확인한 뒤 같은 명령에 `--apply`를 추가합니다. 원본 EPSG:5174 좌표는
웹 지도에서 사용하는 WGS84 좌표로 변환되며, 동명 업소와 미일치 항목은 비워 둡니다.

