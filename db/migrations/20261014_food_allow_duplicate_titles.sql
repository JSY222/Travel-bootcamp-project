-- DataLab may rank different POI IDs with the same displayed restaurant name
-- inside one locality. Source identity remains protected by
-- uq_food_source_record(source_name, source_record_key).
ALTER TABLE food_landmarks
    DROP INDEX uq_food_identity,
    ADD INDEX idx_food_identity (region_code, locality_name, title(191));
