cityname 분류별 SQL 파일 사용 안내
========================================
원본: cityname.sql문.txt
DB: cityname (기존 test DB 불변)

권장 방법 (가장 간단)
  cityname_분류완료.sql을 HeidiSQL에서 열고 전체 SQL 실행(F9)
  파일 첫 부분에 USE `cityname`;이 있으므로 DB 자동 선택

분리된 파일을 사용하는 경우 (반드시 실행 순서 지키기)
  00_테이블생성.sql
  01_지역_출처.sql
  02_관광지.sql
  03_행사.sql
  04_맛집.sql
  05_통합뷰_건수확인.sql

테이블
  regions                 광역 지역 14건
  region_aliases          지역 별칭 31건
  administrative_divisions 시/군/구 정보
  data_sources            데이터 출처, URL, 제공기관 정보 5건
  tourist_attractions     관광지 966건
  events                  행사/축제 10,784건
  restaurants             맛집 148건

통합 조회용 뷰
  v_all_places            관광지/행사/맛집 통합 (원본 landmarks 대체)
  v_landmarks             원본 v_landmarks와 유사한 지역/출처 연결 조회
  v_landmark_counts       지역별/카테고리별 건수

실습 예시
  SELECT * FROM regions;
  SELECT * FROM tourist_attractions WHERE region_id = 10 LIMIT 10;
  SELECT * FROM events WHERE region_id = 1 LIMIT 10;
  SELECT name, source_name, source_url FROM v_landmarks LIMIT 10;

중요
  이 SQL 파일은 7개 대상 테이블을 DROP 후 다시 CREATE합니다.
  cityname에 이미 관련 데이터가 있다면 먼저 백업하세요.
  입력 자료의 행/텍스트/출처 URL은 원본 기준으로 보존했습니다.
  출처 데이터의 최신성/주소/좌표 정확도는 별도 검증하지 않았습니다.
  자료 출처 URL은 data_sources와 v_landmarks에서 확인하세요.
  기존 cityname에 landmarks 테이블이 있다면 이 파일은 그것을 삭제하지 않습니다.
