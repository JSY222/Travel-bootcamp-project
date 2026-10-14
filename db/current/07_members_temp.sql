-- [임시 테스트 파일] members: 테이블 생성만 포함 (회원가입/로그인용, FK 없음 → 순서 무관)
-- app.py가 첫 요청 시 자동 생성하지만, CREATE 권한이 없는 환경에서는 관리자가 미리 실행
-- cityname DB를 선택한 상태에서 실행: mysql cityname < 07_members_temp.sql
-- 확정되면 삭제 예정
SET NAMES utf8mb4;
CREATE TABLE IF NOT EXISTS members (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  name VARCHAR(50) NOT NULL,
  birth_date DATE NOT NULL,
  address VARCHAR(255) NOT NULL,
  travel_styles JSON NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
