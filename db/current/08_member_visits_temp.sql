-- [임시 테스트 파일] member_visits: 테이블 생성만 포함 (방문 기록용, FK 없음 → 순서 무관)
-- visits.py가 조회·저장 시 자동 생성할 예정이지만, CREATE 권한이 없는 환경에서는 관리자가 미리 실행
-- cityname DB를 선택한 상태에서 실행: mysql cityname < 08_member_visits_temp.sql
-- 확정되면 삭제 예정
SET NAMES utf8mb4;
CREATE TABLE IF NOT EXISTS member_visits (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  member_id BIGINT UNSIGNED NOT NULL,
  category VARCHAR(10) NOT NULL,
  landmark_id BIGINT UNSIGNED NOT NULL,
  title VARCHAR(255) NOT NULL,
  locality_name VARCHAR(100) NOT NULL,
  review TEXT NOT NULL,
  photo MEDIUMBLOB NOT NULL,
  photo_mime VARCHAR(30) NOT NULL,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY unique_member_place (member_id, category, landmark_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
