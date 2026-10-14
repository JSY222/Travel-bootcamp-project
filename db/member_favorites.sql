-- Existing travel tables are preserved.
USE cityname;
CREATE TABLE IF NOT EXISTS member_favorites (
    member_id BIGINT UNSIGNED NOT NULL,
    category VARCHAR(10) NOT NULL,
    landmark_id BIGINT UNSIGNED NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (member_id, category, landmark_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
