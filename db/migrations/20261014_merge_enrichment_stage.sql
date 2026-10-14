SET NAMES utf8mb4;
USE `cityname`;
-- Normalize source rows whose region/division metadata disagrees with the
-- leading region and locality in the road address.
UPDATE `cityname_import_stage`.`tourist_attractions` st
JOIN `cityname_import_stage`.`regions` ar
  ON st.road_address COLLATE utf8mb4_unicode_ci LIKE CONCAT(ar.name COLLATE utf8mb4_unicode_ci,' %')
  OR st.road_address COLLATE utf8mb4_unicode_ci LIKE CONCAT(ar.official_name COLLATE utf8mb4_unicode_ci,' %')
LEFT JOIN `cityname_import_stage`.`administrative_divisions` ad
  ON ad.region_id=ar.id
  AND st.road_address COLLATE utf8mb4_unicode_ci LIKE CONCAT('% ',ad.name COLLATE utf8mb4_unicode_ci,' %')
SET st.region_id=ar.id, st.division_id=COALESCE(ad.id,st.division_id)
WHERE st.road_address IS NOT NULL;

UPDATE `cityname_import_stage`.`restaurants` st
JOIN `cityname_import_stage`.`regions` ar
  ON st.road_address COLLATE utf8mb4_unicode_ci LIKE CONCAT(ar.name COLLATE utf8mb4_unicode_ci,' %')
  OR st.road_address COLLATE utf8mb4_unicode_ci LIKE CONCAT(ar.official_name COLLATE utf8mb4_unicode_ci,' %')
LEFT JOIN `cityname_import_stage`.`administrative_divisions` ad
  ON ad.region_id=ar.id
  AND st.road_address COLLATE utf8mb4_unicode_ci LIKE CONCAT('% ',ad.name COLLATE utf8mb4_unicode_ci,' %')
SET st.region_id=ar.id, st.division_id=COALESCE(ad.id,st.division_id)
WHERE st.road_address IS NOT NULL;

UPDATE `cityname_import_stage`.`events` st
JOIN `cityname_import_stage`.`regions` ar
  ON st.road_address COLLATE utf8mb4_unicode_ci LIKE CONCAT(ar.name COLLATE utf8mb4_unicode_ci,' %')
  OR st.road_address COLLATE utf8mb4_unicode_ci LIKE CONCAT(ar.official_name COLLATE utf8mb4_unicode_ci,' %')
LEFT JOIN `cityname_import_stage`.`administrative_divisions` ad
  ON ad.region_id=ar.id
  AND st.road_address COLLATE utf8mb4_unicode_ci LIKE CONCAT('% ',ad.name COLLATE utf8mb4_unicode_ci,' %')
SET st.region_id=ar.id, st.division_id=COALESCE(ad.id,st.division_id)
WHERE st.road_address IS NOT NULL;

-- The one address-less Gwangju-city festival belongs to Gyeonggi-do.
UPDATE `cityname_import_stage`.`events`
SET region_id=9, division_id=147
WHERE region_id=13 AND division_id IS NULL AND name='남한산성문화제';

-- Add newly introduced districts referenced by the source data (for example,
-- Incheon's 2026 administrative reorganization) without removing old rows.
INSERT IGNORE INTO `cityname`.`localities` (`region_code`,`name`,`locality_type`)
SELECT DISTINCT cr.code, ad.name,
       CASE ad.division_type WHEN '시' THEN 'city' WHEN '군' THEN 'county'
            WHEN '구' THEN 'district' ELSE 'other' END
FROM `cityname_import_stage`.`administrative_divisions` ad
JOIN `cityname_import_stage`.`regions` sr ON sr.id=ad.region_id
JOIN `cityname`.`regions` cr
  ON cr.name COLLATE utf8mb4_unicode_ci=sr.name COLLATE utf8mb4_unicode_ci
  OR cr.name COLLATE utf8mb4_unicode_ci=sr.official_name COLLATE utf8mb4_unicode_ci
JOIN (
  SELECT division_id FROM `cityname_import_stage`.`tourist_attractions`
  UNION SELECT division_id FROM `cityname_import_stage`.`restaurants`
  UNION SELECT division_id FROM `cityname_import_stage`.`events`
) used ON used.division_id=ad.id
WHERE ad.name IS NOT NULL;

INSERT IGNORE INTO `cityname`.`localities` (`region_code`,`name`,`locality_type`)
VALUES ('28','제물포구','district'),
       ('28','영종구','district'),
       ('28','서해구','district'),
       ('28','검단구','district');

INSERT INTO `tourist_landmarks`
 (`region_code`,`locality_name`,`title`,`subtype`,`description`,`road_address`,`parcel_address`,
  `latitude`,`longitude`,`phone`,`website_url`,`location_url`,`source_name`,`source_url`,
  `source_priority`,`source_record_key`,`source_updated_date`,`last_verified_at`,`details_json`,`locality_id`)
SELECT cr.code, COALESCE(sd.name,cla.name,sr.name), st.name, st.subtype, st.summary,
       st.road_address, st.parcel_address, st.latitude, st.longitude, st.phone, st.website_url,
       COALESCE(
         CASE WHEN st.latitude IS NOT NULL AND st.longitude IS NOT NULL
           THEN CONCAT('https://www.openstreetmap.org/?mlat=',st.latitude,'&mlon=',st.longitude,'#map=15/',st.latitude,'/',st.longitude) END,
         st.website_url, ss.source_url),
       ss.name, ss.source_url,
       CASE ss.id WHEN 1 THEN 10 ELSE 20 END,
       st.source_record_key, st.source_updated_date, ss.retrieved_at, st.details_json, COALESCE(cl.id,cla.id)
FROM `cityname_import_stage`.`tourist_attractions` st
JOIN `cityname_import_stage`.`regions` sr ON sr.id=st.region_id
JOIN `cityname`.`regions` cr
  ON cr.name COLLATE utf8mb4_unicode_ci=sr.name COLLATE utf8mb4_unicode_ci
  OR cr.name COLLATE utf8mb4_unicode_ci=sr.official_name COLLATE utf8mb4_unicode_ci
LEFT JOIN `cityname_import_stage`.`administrative_divisions` sd ON sd.id=st.division_id
LEFT JOIN `cityname`.`localities` cl
  ON cl.region_code=cr.code
  AND cl.name COLLATE utf8mb4_unicode_ci=sd.name COLLATE utf8mb4_unicode_ci
LEFT JOIN `cityname`.`localities` cla
  ON sd.id IS NULL AND cla.region_code=cr.code
  AND st.road_address COLLATE utf8mb4_unicode_ci LIKE CONCAT(cr.name COLLATE utf8mb4_unicode_ci,' ',cla.name COLLATE utf8mb4_unicode_ci,' %')
JOIN `cityname_import_stage`.`data_sources` ss ON ss.id=st.source_id
ON DUPLICATE KEY UPDATE
 `subtype`=IF(VALUES(`source_priority`)<=`tourist_landmarks`.`source_priority`,COALESCE(VALUES(`subtype`),`tourist_landmarks`.`subtype`),`tourist_landmarks`.`subtype`),
 `description`=IF(VALUES(`source_priority`)<=`tourist_landmarks`.`source_priority`,COALESCE(VALUES(`description`),`tourist_landmarks`.`description`),`tourist_landmarks`.`description`),
 `road_address`=IF(VALUES(`source_priority`)<=`tourist_landmarks`.`source_priority`,COALESCE(VALUES(`road_address`),`tourist_landmarks`.`road_address`),`tourist_landmarks`.`road_address`),
 `parcel_address`=IF(VALUES(`source_priority`)<=`tourist_landmarks`.`source_priority`,COALESCE(VALUES(`parcel_address`),`tourist_landmarks`.`parcel_address`),`tourist_landmarks`.`parcel_address`),
 `latitude`=COALESCE(VALUES(`latitude`),`tourist_landmarks`.`latitude`), `longitude`=COALESCE(VALUES(`longitude`),`tourist_landmarks`.`longitude`),
 `phone`=COALESCE(VALUES(`phone`),`tourist_landmarks`.`phone`), `website_url`=COALESCE(VALUES(`website_url`),`tourist_landmarks`.`website_url`),
 `location_url`=COALESCE(VALUES(`location_url`),`tourist_landmarks`.`location_url`),
 `source_name`=IF(VALUES(`source_priority`)<=`tourist_landmarks`.`source_priority`,VALUES(`source_name`),`tourist_landmarks`.`source_name`),
 `source_url`=IF(VALUES(`source_priority`)<=`tourist_landmarks`.`source_priority`,VALUES(`source_url`),`tourist_landmarks`.`source_url`),
 `source_priority`=LEAST(`tourist_landmarks`.`source_priority`,VALUES(`source_priority`)),
 `source_record_key`=IF(VALUES(`source_priority`)<=`tourist_landmarks`.`source_priority`,VALUES(`source_record_key`),`tourist_landmarks`.`source_record_key`),
 `source_updated_date`=GREATEST(COALESCE(`tourist_landmarks`.`source_updated_date`,'1000-01-01'),COALESCE(VALUES(`source_updated_date`),'1000-01-01')),
 `last_verified_at`=GREATEST(COALESCE(`tourist_landmarks`.`last_verified_at`,'1000-01-01'),COALESCE(VALUES(`last_verified_at`),'1000-01-01')),
 `details_json`=IF(VALUES(`source_priority`)<=`tourist_landmarks`.`source_priority`,COALESCE(VALUES(`details_json`),`tourist_landmarks`.`details_json`),`tourist_landmarks`.`details_json`),
 `locality_id`=COALESCE(VALUES(`locality_id`),`tourist_landmarks`.`locality_id`);

INSERT INTO `food_landmarks`
 (`region_code`,`locality_name`,`title`,`subtype`,`description`,`road_address`,`parcel_address`,
  `latitude`,`longitude`,`phone`,`website_url`,`location_url`,`source_name`,`source_url`,
  `source_priority`,`source_record_key`,`source_updated_date`,`last_verified_at`,`rating`,`review_count`,`details_json`,`locality_id`)
SELECT cr.code, COALESCE(sd.name,cla.name,sr.name), st.name, st.subtype, st.summary,
       st.road_address, st.parcel_address, st.latitude, st.longitude, st.phone, st.website_url,
       COALESCE(
         CASE WHEN st.latitude IS NOT NULL AND st.longitude IS NOT NULL
           THEN CONCAT('https://www.openstreetmap.org/?mlat=',st.latitude,'&mlon=',st.longitude,'#map=15/',st.latitude,'/',st.longitude) END,
         st.website_url, ss.source_url),
       ss.name, ss.source_url,
       CASE ss.id WHEN 5 THEN 15 WHEN 4 THEN 30 ELSE 40 END,
       st.source_record_key, st.source_updated_date, ss.retrieved_at, st.rating, st.review_count, st.details_json, COALESCE(cl.id,cla.id)
FROM `cityname_import_stage`.`restaurants` st
JOIN `cityname_import_stage`.`regions` sr ON sr.id=st.region_id
JOIN `cityname`.`regions` cr
  ON cr.name COLLATE utf8mb4_unicode_ci=sr.name COLLATE utf8mb4_unicode_ci
  OR cr.name COLLATE utf8mb4_unicode_ci=sr.official_name COLLATE utf8mb4_unicode_ci
LEFT JOIN `cityname_import_stage`.`administrative_divisions` sd ON sd.id=st.division_id
LEFT JOIN `cityname`.`localities` cl
  ON cl.region_code=cr.code
  AND cl.name COLLATE utf8mb4_unicode_ci=sd.name COLLATE utf8mb4_unicode_ci
LEFT JOIN `cityname`.`localities` cla
  ON sd.id IS NULL AND cla.region_code=cr.code
  AND st.road_address COLLATE utf8mb4_unicode_ci LIKE CONCAT(cr.name COLLATE utf8mb4_unicode_ci,' ',cla.name COLLATE utf8mb4_unicode_ci,' %')
JOIN `cityname_import_stage`.`data_sources` ss ON ss.id=st.source_id
ON DUPLICATE KEY UPDATE
 `subtype`=IF(VALUES(`source_priority`)<=`food_landmarks`.`source_priority`,COALESCE(VALUES(`subtype`),`food_landmarks`.`subtype`),`food_landmarks`.`subtype`),
 `description`=IF(VALUES(`source_priority`)<=`food_landmarks`.`source_priority`,COALESCE(VALUES(`description`),`food_landmarks`.`description`),`food_landmarks`.`description`),
 `road_address`=IF(VALUES(`source_priority`)<=`food_landmarks`.`source_priority`,COALESCE(VALUES(`road_address`),`food_landmarks`.`road_address`),`food_landmarks`.`road_address`),
 `parcel_address`=IF(VALUES(`source_priority`)<=`food_landmarks`.`source_priority`,COALESCE(VALUES(`parcel_address`),`food_landmarks`.`parcel_address`),`food_landmarks`.`parcel_address`),
 `latitude`=COALESCE(VALUES(`latitude`),`food_landmarks`.`latitude`), `longitude`=COALESCE(VALUES(`longitude`),`food_landmarks`.`longitude`),
 `phone`=COALESCE(VALUES(`phone`),`food_landmarks`.`phone`), `website_url`=COALESCE(VALUES(`website_url`),`food_landmarks`.`website_url`),
 `location_url`=COALESCE(VALUES(`location_url`),`food_landmarks`.`location_url`),
 `source_name`=IF(VALUES(`source_priority`)<=`food_landmarks`.`source_priority`,VALUES(`source_name`),`food_landmarks`.`source_name`),
 `source_url`=IF(VALUES(`source_priority`)<=`food_landmarks`.`source_priority`,VALUES(`source_url`),`food_landmarks`.`source_url`),
 `source_priority`=LEAST(`food_landmarks`.`source_priority`,VALUES(`source_priority`)),
 `source_record_key`=IF(VALUES(`source_priority`)<=`food_landmarks`.`source_priority`,VALUES(`source_record_key`),`food_landmarks`.`source_record_key`),
 `source_updated_date`=GREATEST(COALESCE(`food_landmarks`.`source_updated_date`,'1000-01-01'),COALESCE(VALUES(`source_updated_date`),'1000-01-01')),
 `last_verified_at`=GREATEST(COALESCE(`food_landmarks`.`last_verified_at`,'1000-01-01'),COALESCE(VALUES(`last_verified_at`),'1000-01-01')),
 `rating`=COALESCE(VALUES(`rating`),`food_landmarks`.`rating`), `review_count`=COALESCE(VALUES(`review_count`),`food_landmarks`.`review_count`),
 `details_json`=IF(VALUES(`source_priority`)<=`food_landmarks`.`source_priority`,COALESCE(VALUES(`details_json`),`food_landmarks`.`details_json`),`food_landmarks`.`details_json`),
 `locality_id`=COALESCE(VALUES(`locality_id`),`food_landmarks`.`locality_id`);

INSERT INTO `event_landmarks`
 (`region_code`,`locality_name`,`title`,`subtype`,`description`,`road_address`,`parcel_address`,
  `latitude`,`longitude`,`phone`,`website_url`,`venue`,`start_date`,`end_date`,`start_time`,`end_time`,
  `fee_info`,`organizer`,`event_status`,`location_url`,`source_name`,`source_url`,`source_priority`,
  `source_record_key`,`source_updated_date`,`last_verified_at`,`details_json`,`locality_id`)
SELECT cr.code, COALESCE(sd.name,cla.name,sr.name), st.name, st.subtype, st.summary,
       st.road_address, st.parcel_address, st.latitude, st.longitude, st.phone, st.website_url,
       st.venue, st.start_date, st.end_date, st.start_time, st.end_time, st.fee_info, st.organizer,
       CASE WHEN st.end_date IS NULL AND st.start_date IS NULL THEN 'unknown'
            WHEN st.end_date < CURRENT_DATE THEN 'ended'
            WHEN st.start_date > CURRENT_DATE THEN 'scheduled' ELSE 'ongoing' END,
       COALESCE(
         CASE WHEN st.latitude IS NOT NULL AND st.longitude IS NOT NULL
           THEN CONCAT('https://www.openstreetmap.org/?mlat=',st.latitude,'&mlon=',st.longitude,'#map=15/',st.latitude,'/',st.longitude) END,
         st.website_url, ss.source_url),
       ss.name, ss.source_url,
       CASE ss.id WHEN 2 THEN 10 WHEN 3 THEN 20 ELSE 40 END,
       st.source_record_key, st.source_updated_date, ss.retrieved_at, st.details_json, COALESCE(cl.id,cla.id)
FROM `cityname_import_stage`.`events` st
JOIN `cityname_import_stage`.`regions` sr ON sr.id=st.region_id
JOIN `cityname`.`regions` cr
  ON cr.name COLLATE utf8mb4_unicode_ci=sr.name COLLATE utf8mb4_unicode_ci
  OR cr.name COLLATE utf8mb4_unicode_ci=sr.official_name COLLATE utf8mb4_unicode_ci
LEFT JOIN `cityname_import_stage`.`administrative_divisions` sd ON sd.id=st.division_id
LEFT JOIN `cityname`.`localities` cl
  ON cl.region_code=cr.code
  AND cl.name COLLATE utf8mb4_unicode_ci=sd.name COLLATE utf8mb4_unicode_ci
LEFT JOIN `cityname`.`localities` cla
  ON sd.id IS NULL AND cla.region_code=cr.code
  AND st.road_address COLLATE utf8mb4_unicode_ci LIKE CONCAT(cr.name COLLATE utf8mb4_unicode_ci,' ',cla.name COLLATE utf8mb4_unicode_ci,' %')
JOIN `cityname_import_stage`.`data_sources` ss ON ss.id=st.source_id
WHERE st.end_date IS NULL OR st.end_date >= CURRENT_DATE - INTERVAL 365 DAY
ON DUPLICATE KEY UPDATE
 `subtype`=IF(VALUES(`source_priority`)<=`event_landmarks`.`source_priority`,COALESCE(VALUES(`subtype`),`event_landmarks`.`subtype`),`event_landmarks`.`subtype`),
 `description`=IF(VALUES(`source_priority`)<=`event_landmarks`.`source_priority`,COALESCE(VALUES(`description`),`event_landmarks`.`description`),`event_landmarks`.`description`),
 `road_address`=IF(VALUES(`source_priority`)<=`event_landmarks`.`source_priority`,COALESCE(VALUES(`road_address`),`event_landmarks`.`road_address`),`event_landmarks`.`road_address`),
 `parcel_address`=IF(VALUES(`source_priority`)<=`event_landmarks`.`source_priority`,COALESCE(VALUES(`parcel_address`),`event_landmarks`.`parcel_address`),`event_landmarks`.`parcel_address`),
 `latitude`=COALESCE(VALUES(`latitude`),`event_landmarks`.`latitude`), `longitude`=COALESCE(VALUES(`longitude`),`event_landmarks`.`longitude`),
 `phone`=COALESCE(VALUES(`phone`),`event_landmarks`.`phone`), `website_url`=COALESCE(VALUES(`website_url`),`event_landmarks`.`website_url`),
 `venue`=COALESCE(VALUES(`venue`),`event_landmarks`.`venue`), `start_date`=COALESCE(VALUES(`start_date`),`event_landmarks`.`start_date`),
 `end_date`=COALESCE(VALUES(`end_date`),`event_landmarks`.`end_date`), `start_time`=COALESCE(VALUES(`start_time`),`event_landmarks`.`start_time`),
 `end_time`=COALESCE(VALUES(`end_time`),`event_landmarks`.`end_time`), `fee_info`=COALESCE(VALUES(`fee_info`),`event_landmarks`.`fee_info`),
 `organizer`=COALESCE(VALUES(`organizer`),`event_landmarks`.`organizer`), `event_status`=VALUES(`event_status`),
 `location_url`=COALESCE(VALUES(`location_url`),`event_landmarks`.`location_url`),
 `source_name`=IF(VALUES(`source_priority`)<=`event_landmarks`.`source_priority`,VALUES(`source_name`),`event_landmarks`.`source_name`),
 `source_url`=IF(VALUES(`source_priority`)<=`event_landmarks`.`source_priority`,VALUES(`source_url`),`event_landmarks`.`source_url`),
 `source_priority`=LEAST(`event_landmarks`.`source_priority`,VALUES(`source_priority`)),
 `source_record_key`=IF(VALUES(`source_priority`)<=`event_landmarks`.`source_priority`,VALUES(`source_record_key`),`event_landmarks`.`source_record_key`),
 `source_updated_date`=GREATEST(COALESCE(`event_landmarks`.`source_updated_date`,'1000-01-01'),COALESCE(VALUES(`source_updated_date`),'1000-01-01')),
 `last_verified_at`=GREATEST(COALESCE(`event_landmarks`.`last_verified_at`,'1000-01-01'),COALESCE(VALUES(`last_verified_at`),'1000-01-01')),
 `details_json`=IF(VALUES(`source_priority`)<=`event_landmarks`.`source_priority`,COALESCE(VALUES(`details_json`),`event_landmarks`.`details_json`),`event_landmarks`.`details_json`),
 `locality_id`=COALESCE(VALUES(`locality_id`),`event_landmarks`.`locality_id`);

SET FOREIGN_KEY_CHECKS = 1;

-- Verification result sets.
SELECT 'tourist_landmarks' AS table_name, COUNT(*) AS row_count,
       SUM(latitude IS NOT NULL AND longitude IS NOT NULL) AS mappable_count
FROM `tourist_landmarks`
UNION ALL
SELECT 'food_landmarks', COUNT(*), SUM(latitude IS NOT NULL AND longitude IS NOT NULL)
FROM `food_landmarks`
UNION ALL
SELECT 'event_landmarks', COUNT(*), SUM(latitude IS NOT NULL AND longitude IS NOT NULL)
FROM `event_landmarks`;

SELECT `source_name`, COUNT(*) AS row_count
FROM (
  SELECT source_name FROM tourist_landmarks
  UNION ALL SELECT source_name FROM food_landmarks
  UNION ALL SELECT source_name FROM event_landmarks
) sources
GROUP BY source_name
ORDER BY row_count DESC;
