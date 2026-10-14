-- [임시 테스트 파일] regions: 테이블 생성 + 기준 데이터(17개 시도) 삽입
-- cityname DB를 선택한 상태에서 실행: mysql cityname < 01_regions_temp.sql
-- 확정되면 삭제 예정
SET NAMES utf8mb4;
CREATE TABLE IF NOT EXISTS regions (
  code CHAR(2) PRIMARY KEY,
  name VARCHAR(50) NOT NULL,
  region_type ENUM('province','metro') NOT NULL,
  display_order TINYINT UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO regions(code,name,region_type,display_order) VALUES
  ('47','경상북도','province',1),
  ('48','경상남도','province',2),
  ('45','전라북도','province',3),
  ('46','전라남도','province',4),
  ('50','제주특별자치도','province',5),
  ('42','강원도','province',6),
  ('43','충청북도','province',7),
  ('44','충청남도','province',8),
  ('41','경기도','province',9),
  ('11','서울특별시','metro',10),
  ('27','대구광역시','metro',11),
  ('26','부산광역시','metro',12),
  ('29','광주광역시','metro',13),
  ('28','인천광역시','metro',14),
  ('30','대전광역시','metro',15),
  ('31','울산광역시','metro',16),
  ('36','세종특별자치시','metro',17)
ON DUPLICATE KEY UPDATE
  name=VALUES(name), region_type=VALUES(region_type), display_order=VALUES(display_order);
