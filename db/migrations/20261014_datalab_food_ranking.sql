-- 한국관광 데이터랩 지역 맛집 순위 메타데이터
ALTER TABLE food_landmarks
  ADD COLUMN IF NOT EXISTS area_rank SMALLINT UNSIGNED NULL AFTER review_count,
  ADD COLUMN IF NOT EXISTS ranking_scope VARCHAR(100) NULL AFTER area_rank,
  ADD COLUMN IF NOT EXISTS ranking_period_start CHAR(6) NULL AFTER ranking_scope,
  ADD COLUMN IF NOT EXISTS ranking_period_end CHAR(6) NULL AFTER ranking_period_start,
  ADD COLUMN IF NOT EXISTS datalab_poi_id CHAR(32) NULL AFTER ranking_period_end,
  ADD COLUMN IF NOT EXISTS tourapi_content_id VARCHAR(30) NULL AFTER datalab_poi_id,
  ADD COLUMN IF NOT EXISTS tourapi_match_score DECIMAL(5,4) NULL AFTER tourapi_content_id,
  ADD COLUMN IF NOT EXISTS image_url VARCHAR(2000) NULL AFTER tourapi_match_score,
  ADD KEY IF NOT EXISTS idx_food_area_rank (region_code, locality_name, area_rank);

