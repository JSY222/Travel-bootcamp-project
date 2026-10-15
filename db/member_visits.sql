-- Existing travel tables are preserved.
USE cityname;
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
    visited_on DATE NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY member_place (member_id, category, landmark_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
