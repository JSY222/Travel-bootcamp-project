-- 원래 landmarks 테이블처럼 세 범주를 한꺼번에 조회하는 통합 뷰
USE `cityname`;

CREATE OR REPLACE VIEW `v_all_places` AS
SELECT * FROM `tourist_attractions`
UNION ALL
SELECT * FROM `events`
UNION ALL
SELECT * FROM `restaurants`;

-- 지역명/시군구명/출처와 URL까지 함께 조회할 수 있는 뷰
CREATE OR REPLACE VIEW `v_landmarks` AS
SELECT p.*, r.name AS region_name, r.official_name AS region_official_name,
       d.name AS division_name, s.name AS source_name, s.source_url
FROM `v_all_places` AS p
JOIN `regions` AS r ON r.id = p.region_id
LEFT JOIN `administrative_divisions` AS d ON d.id = p.division_id
JOIN `data_sources` AS s ON s.id = p.source_id;

-- 지역별 데이터 건수
CREATE OR REPLACE VIEW `v_landmark_counts` AS
SELECT r.name AS region_name, p.category, COUNT(*) AS landmark_count
FROM `v_all_places` AS p
JOIN `regions` AS r ON r.id = p.region_id
GROUP BY r.id, r.name, p.category;

-- 분류 후 행 수 확인: 관광지 966 / 행사 10784 / 맛집 148
SELECT 'regions' AS table_name, COUNT(*) AS row_count FROM `regions`
UNION ALL SELECT 'administrative_divisions', COUNT(*) FROM `administrative_divisions`
UNION ALL SELECT 'tourist_attractions', COUNT(*) FROM `tourist_attractions`
UNION ALL SELECT 'events', COUNT(*) FROM `events`
UNION ALL SELECT 'restaurants', COUNT(*) FROM `restaurants`
UNION ALL SELECT 'data_sources', COUNT(*) FROM `data_sources`;
