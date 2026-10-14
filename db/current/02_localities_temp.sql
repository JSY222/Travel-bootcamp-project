-- [임시 테스트 파일] localities: 테이블 생성만 포함 (regions 다음에 실행)
-- 실제 데이터는 수작업 INSERT 없이 import_geojson_regions.py 실행으로 채워짐
-- cityname DB를 선택한 상태에서 실행: mysql cityname < 02_localities_temp.sql
-- 확정되면 삭제 예정
SET NAMES utf8mb4;
CREATE TABLE IF NOT EXISTS localities (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  region_code CHAR(2) NOT NULL,
  name VARCHAR(50) NOT NULL,
  locality_type ENUM('city','county','district','town','other') NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_locality_region_name (region_code, name),
  CONSTRAINT fk_localities_region FOREIGN KEY (region_code) REFERENCES regions(code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
