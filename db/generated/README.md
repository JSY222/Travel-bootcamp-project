# 데이터랩 맛집 순위 가져오기

`datalab_food_rankings.sql`은 `db/data/datalab_food_top20` 아래 ZIP과 CSV에서 생성한 MariaDB용 쿼리입니다. 2026-10-14 사용자 요청으로 설정된 `cityname` DB에 실행했고, 순위 25,500건·지역 85개·TOP20 5,100건을 확인했습니다.

## 포함 자료

- 지역 85개, 25,500건: 전체·현지인·외지인 각 8,500건.
- 원본은 분류별 100위까지 포함하므로 모두 보존합니다. `v_datalab_food_top20` 뷰는 원본 순위 20위 이내 5,100건을 조회합니다. 공동 순위는 재계산하지 않습니다.
- 원본 기간 `202507-202606`, `202510-202609`를 구분합니다. 지역마다 제공 기간이 다를 수 있습니다.
- ZIP과 압축 해제 폴더, `(2)` 폴더의 동일 자료는 합칩니다. 이번 자료에서 중복 행 9,900건을 제외했습니다. 동일 키에 서로 다른 원본 내용이 있으면 SQL 생성을 중단합니다.

## 실행

MariaDB에서 `cityname` DB가 준비된 상태로 SQL 파일을 열어 전체 실행합니다. MariaDB CLI에서는 다음과 같이 실행할 수도 있습니다.

```sql
SOURCE C:/Users/user/Documents/GitHub/Travel-bootcamp-project/db/generated/datalab_food_rankings.sql;
```

새 테이블 `datalab_food_rankings`와 뷰 `v_datalab_food_top20`를 생성합니다. 기본키는 `(sigungu_code, period_start, period_end, audience, poi_id)`입니다. 재실행하면 같은 키의 이름·분류·순위를 갱신하고 중복 행은 추가하지 않습니다. 새 원본에서 빠진 행을 자동 삭제하지는 않습니다. 테이블 생성과 뷰 생성은 MariaDB DDL이므로 DML 트랜잭션과 별도로 적용됩니다.

기존 `food_landmarks`, 회원, 방문 기록, 즐겨찾기를 삭제하거나 변경하지 않습니다. 원본에는 주소·좌표가 없어 이 SQL만으로 지도에 새 맛집 마커가 생기지는 않습니다. 지도 연결은 주소·좌표 보강 후 별도 적용해야 합니다.

## 조회

```sql
-- 종로구, 전체 방문자 기준 TOP20. 기간이 다른 자료는 따로 조회합니다.
SELECT area_rank, title, subtype, poi_id
FROM v_datalab_food_top20
WHERE sigungu_code = '11110'
  AND audience = 'all'
  AND period_start = '202510' AND period_end = '202609'
ORDER BY area_rank, poi_id;

-- 분류별 저장 건수
SELECT audience, COUNT(*) FROM datalab_food_rankings GROUP BY audience;
```

`audience`: `all` 전체, `local` 현지인, `nonlocal` 외지인. `sigungu_code`는 파일명의 5자리 시군구 코드이며, 기존 `geo_admin_codes`와 DB 외래키로 묶지는 않습니다.

## 재생성·검증

```text
python db/generate_datalab_food_sql.py
python -m unittest discover -s tests -p test_datalab_food_sql.py
```

DB 접속이나 외부 API 없이 생성합니다. 건수 보고서는 `datalab_food_rankings.report.json`입니다. 문자열은 UTF-8 16진 리터럴로 출력하므로 한글·따옴표·역슬래시와 SQL 모드 차이로 인한 깨짐을 피합니다.

## Flask 웹 연결

`food_rankings.py`의 `/api/food-rankings/options`와 `/api/food-rankings`가 저장된 자료를 조회합니다. 왼쪽 패널의 ‘데이터랩 맛집 TOP20’에서 지역·기간·방문자 구분을 선택합니다. 지도에서 지역을 선택해도 해당 시·도의 자료로 연결됩니다. 원본 좌표가 없으므로 지도 마커, 방문 기록, 즐겨찾기와는 별도 순위 목록입니다.

실제 DB를 사용해 API의 85개 지역 목록과 종로구 TOP20 반환, 잘못된 조건 거부, 지도 HTML 렌더링을 검증했습니다. 브라우저 화면은 별도 확인이 필요합니다. SQL 재실행용 Python 도구는 `db/apply_datalab_food_sql.py`이며 프로젝트 `.env`의 DB 접속 정보를 사용합니다.
