-- [임시 테스트 파일] geo_admin_codes: 테이블 생성만 포함 (localities 다음에 실행)
-- 실제 데이터는 수작업 INSERT 없이 import_geojson_regions.py 실행으로 채워짐
-- cityname DB를 선택한 상태에서 실행: mysql cityname < 03_geo_admin_codes_temp.sql
-- 확정되면 삭제 예정
SET NAMES utf8mb4;
CREATE TABLE IF NOT EXISTS geo_admin_codes (
  source_level ENUM('SIG','EMD') NOT NULL,
  source_code VARCHAR(10) NOT NULL,
  locality_id INT UNSIGNED NOT NULL,
  PRIMARY KEY (source_level, source_code),
  CONSTRAINT fk_geo_admin_codes_locality FOREIGN KEY (locality_id) REFERENCES localities(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
