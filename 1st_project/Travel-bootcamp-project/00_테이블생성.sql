-- =============================================================
-- cityname DB: 지역 / 관광지 / 행사 / 맛집별 분리 SQL
-- 원본: 사용자가 제공한 cityname.sql문.txt (travel_landmarks 자료)
-- MariaDB 10.5+ / UTF-8 (utf8mb4)
-- ※ 주의: 같은 이름의 대상 테이블 7개를 삭제 후 다시 만듭니다.
-- ※ 기존 test DB는 건드리지 않습니다. 기존 cityname 데이터는 백업하세요.
-- =============================================================
SET NAMES utf8mb4;
CREATE DATABASE IF NOT EXISTS `cityname`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `cityname`;

SET FOREIGN_KEY_CHECKS = 0;
DROP VIEW IF EXISTS `v_landmark_counts`;
DROP VIEW IF EXISTS `v_landmarks`;
DROP VIEW IF EXISTS `v_all_places`;
DROP TABLE IF EXISTS `tourist_attractions`;
DROP TABLE IF EXISTS `events`;
DROP TABLE IF EXISTS `restaurants`;
DROP TABLE IF EXISTS `administrative_divisions`;
DROP TABLE IF EXISTS `region_aliases`;
DROP TABLE IF EXISTS `data_sources`;
DROP TABLE IF EXISTS `regions`;

-- 지역(시/도) / 지역 별칭 / 시군구 / 출처
CREATE TABLE regions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    official_name VARCHAR(50) NOT NULL,
    region_type VARCHAR(20) NOT NULL,
    center_latitude DECIMAL(10,7) NULL,
    center_longitude DECIMAL(10,7) NULL,
    default_zoom DECIMAL(4,1) NULL,
    geojson LONGTEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_regions_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE region_aliases (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    region_id BIGINT UNSIGNED NOT NULL,
    alias VARCHAR(50) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_region_alias (alias),
    KEY idx_region_alias_region (region_id),
    CONSTRAINT fk_region_alias_region
      FOREIGN KEY (region_id) REFERENCES regions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE administrative_divisions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    region_id BIGINT UNSIGNED NOT NULL,
    name VARCHAR(80) NOT NULL,
    division_type VARCHAR(20) NOT NULL,
    admin_code VARCHAR(30) NULL,
    center_latitude DECIMAL(10,7) NULL,
    center_longitude DECIMAL(10,7) NULL,
    geojson LONGTEXT NULL,
    is_current TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (id),
    UNIQUE KEY uq_division_region_name (region_id, name),
    KEY idx_divisions_region (region_id, division_type, name),
    CONSTRAINT fk_division_region
      FOREIGN KEY (region_id) REFERENCES regions(id) ON DELETE CASCADE,
    CONSTRAINT chk_division_current CHECK (is_current IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE data_sources (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(150) NOT NULL,
    source_url VARCHAR(1000) NOT NULL,
    provider VARCHAR(255) NULL,
    license_note VARCHAR(500) NULL,
    retrieved_at DATE NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_data_source_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 관광지 테이블 / 행사 테이블 / 맛집 테이블
CREATE TABLE `tourist_attractions` (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    region_id BIGINT UNSIGNED NOT NULL,
    division_id BIGINT UNSIGNED NULL,
    category VARCHAR(20) NOT NULL,
    subtype VARCHAR(80) NULL,
    name VARCHAR(500) NOT NULL,
    summary LONGTEXT NULL,
    road_address VARCHAR(1000) NULL,
    parcel_address VARCHAR(1000) NULL,
    latitude DECIMAL(11,8) NULL,
    longitude DECIMAL(11,8) NULL,
    phone VARCHAR(255) NULL,
    website_url VARCHAR(2000) NULL,
    venue VARCHAR(1000) NULL,
    start_date DATE NULL,
    end_date DATE NULL,
    start_time VARCHAR(30) NULL,
    end_time VARCHAR(30) NULL,
    fee_info LONGTEXT NULL,
    parking_info VARCHAR(500) NULL,
    organizer VARCHAR(500) NULL,
    managing_agency VARCHAR(500) NULL,
    rating DECIMAL(4,2) NULL,
    review_count INT UNSIGNED NULL,
    source_id BIGINT UNSIGNED NOT NULL,
    source_record_key CHAR(64) NOT NULL,
    source_updated_date DATE NULL,
    details_json LONGTEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_tourist_source_record (source_id, source_record_key),
    KEY idx_tourist_region_category (region_id, category),
    KEY idx_tourist_division (division_id),
    KEY idx_tourist_dates (start_date, end_date),
    KEY idx_tourist_coordinates (latitude, longitude),
    FULLTEXT KEY ft_tourist_search (name, summary, road_address, category, subtype),
    CONSTRAINT fk_tourist_region
      FOREIGN KEY (region_id) REFERENCES regions(id),
    CONSTRAINT fk_tourist_division
      FOREIGN KEY (division_id) REFERENCES administrative_divisions(id),
    CONSTRAINT fk_tourist_source
      FOREIGN KEY (source_id) REFERENCES data_sources(id),
    CONSTRAINT chk_tourist_category CHECK (category = '관광지')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `events` (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    region_id BIGINT UNSIGNED NOT NULL,
    division_id BIGINT UNSIGNED NULL,
    category VARCHAR(20) NOT NULL,
    subtype VARCHAR(80) NULL,
    name VARCHAR(500) NOT NULL,
    summary LONGTEXT NULL,
    road_address VARCHAR(1000) NULL,
    parcel_address VARCHAR(1000) NULL,
    latitude DECIMAL(11,8) NULL,
    longitude DECIMAL(11,8) NULL,
    phone VARCHAR(255) NULL,
    website_url VARCHAR(2000) NULL,
    venue VARCHAR(1000) NULL,
    start_date DATE NULL,
    end_date DATE NULL,
    start_time VARCHAR(30) NULL,
    end_time VARCHAR(30) NULL,
    fee_info LONGTEXT NULL,
    parking_info VARCHAR(500) NULL,
    organizer VARCHAR(500) NULL,
    managing_agency VARCHAR(500) NULL,
    rating DECIMAL(4,2) NULL,
    review_count INT UNSIGNED NULL,
    source_id BIGINT UNSIGNED NOT NULL,
    source_record_key CHAR(64) NOT NULL,
    source_updated_date DATE NULL,
    details_json LONGTEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_event_source_record (source_id, source_record_key),
    KEY idx_event_region_category (region_id, category),
    KEY idx_event_division (division_id),
    KEY idx_event_dates (start_date, end_date),
    KEY idx_event_coordinates (latitude, longitude),
    FULLTEXT KEY ft_event_search (name, summary, road_address, category, subtype),
    CONSTRAINT fk_event_region
      FOREIGN KEY (region_id) REFERENCES regions(id),
    CONSTRAINT fk_event_division
      FOREIGN KEY (division_id) REFERENCES administrative_divisions(id),
    CONSTRAINT fk_event_source
      FOREIGN KEY (source_id) REFERENCES data_sources(id),
    CONSTRAINT chk_event_category CHECK (category = '행사')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `restaurants` (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    region_id BIGINT UNSIGNED NOT NULL,
    division_id BIGINT UNSIGNED NULL,
    category VARCHAR(20) NOT NULL,
    subtype VARCHAR(80) NULL,
    name VARCHAR(500) NOT NULL,
    summary LONGTEXT NULL,
    road_address VARCHAR(1000) NULL,
    parcel_address VARCHAR(1000) NULL,
    latitude DECIMAL(11,8) NULL,
    longitude DECIMAL(11,8) NULL,
    phone VARCHAR(255) NULL,
    website_url VARCHAR(2000) NULL,
    venue VARCHAR(1000) NULL,
    start_date DATE NULL,
    end_date DATE NULL,
    start_time VARCHAR(30) NULL,
    end_time VARCHAR(30) NULL,
    fee_info LONGTEXT NULL,
    parking_info VARCHAR(500) NULL,
    organizer VARCHAR(500) NULL,
    managing_agency VARCHAR(500) NULL,
    rating DECIMAL(4,2) NULL,
    review_count INT UNSIGNED NULL,
    source_id BIGINT UNSIGNED NOT NULL,
    source_record_key CHAR(64) NOT NULL,
    source_updated_date DATE NULL,
    details_json LONGTEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_restaurant_source_record (source_id, source_record_key),
    KEY idx_restaurant_region_category (region_id, category),
    KEY idx_restaurant_division (division_id),
    KEY idx_restaurant_dates (start_date, end_date),
    KEY idx_restaurant_coordinates (latitude, longitude),
    FULLTEXT KEY ft_restaurant_search (name, summary, road_address, category, subtype),
    CONSTRAINT fk_restaurant_region
      FOREIGN KEY (region_id) REFERENCES regions(id),
    CONSTRAINT fk_restaurant_division
      FOREIGN KEY (division_id) REFERENCES administrative_divisions(id),
    CONSTRAINT fk_restaurant_source
      FOREIGN KEY (source_id) REFERENCES data_sources(id),
    CONSTRAINT chk_restaurant_category CHECK (category = '맛집')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
