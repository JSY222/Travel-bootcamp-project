-- [임시 테스트 파일] member_favorites: 테이블 생성만 포함 (즐겨찾기용, FK 없음 → 순서 무관)
-- favorites.py가 조회·저장 시 자동 생성할 예정이지만, CREATE 권한이 없는 환경에서는 관리자가 미리 실행
-- cityname DB를 선택한 상태에서 실행: mysql cityname < 09_member_favorites_temp.sql
-- 확정되면 삭제 예정
SET NAMES utf8mb4;
CREATE TABLE IF NOT EXISTS member_favorites (
  member_id BIGINT UNSIGNED NOT NULL,
  category VARCHAR(10) NOT NULL,
  landmark_id BIGINT UNSIGNED NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (member_id, category, landmark_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
