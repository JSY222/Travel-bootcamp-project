-- cityname DB의 현재 테이블 구조만 생성합니다 (데이터 없음, 기존 테이블/데이터는 건드리지 않음).
-- 새 환경을 처음 준비할 때 먼저 이 파일을 실행하세요.
-- 그 다음 regions 마스터 데이터는 cityname_landmarks_1013.sql에서 INSERT 문만 가져오거나
-- 직접 INSERT 하고, 나머지는 import_geojson_regions.py 또는 API 연동으로 채우면 됩니다.
CREATE DATABASE IF NOT EXISTS `cityname` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `cityname`;
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS regions (
  code CHAR(2) PRIMARY KEY,
  name VARCHAR(50) NOT NULL,
  region_type ENUM('province','metro') NOT NULL,
  display_order TINYINT UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS localities (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  region_code CHAR(2) NOT NULL,
  name VARCHAR(50) NOT NULL,
  locality_type ENUM('city','county','district','town','other') NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_locality_region_name (region_code, name),
  CONSTRAINT fk_localities_region FOREIGN KEY (region_code) REFERENCES regions(code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS geo_admin_codes (
  source_level ENUM('SIG','EMD') NOT NULL,
  source_code VARCHAR(10) NOT NULL,
  locality_id INT UNSIGNED NOT NULL,
  PRIMARY KEY (source_level, source_code),
  CONSTRAINT fk_geo_admin_codes_locality FOREIGN KEY (locality_id) REFERENCES localities(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `tourist_landmarks` (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  region_code CHAR(2) NOT NULL,
  locality_name VARCHAR(50) NOT NULL,
  title VARCHAR(120) NOT NULL,
  description VARCHAR(255) NOT NULL,
  latitude DECIMAL(10,6) NOT NULL,
  longitude DECIMAL(10,6) NOT NULL,
  location_url VARCHAR(500) NOT NULL,
  source_name VARCHAR(100) NOT NULL,
  INDEX idx_lookup(region_code, locality_name),
  CONSTRAINT fk_tourist_landmarks_region FOREIGN KEY (region_code) REFERENCES regions(code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `food_landmarks` (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  region_code CHAR(2) NOT NULL,
  locality_name VARCHAR(50) NOT NULL,
  title VARCHAR(120) NOT NULL,
  description VARCHAR(255) NOT NULL,
  latitude DECIMAL(10,6) NOT NULL,
  longitude DECIMAL(10,6) NOT NULL,
  location_url VARCHAR(500) NOT NULL,
  source_name VARCHAR(100) NOT NULL,
  INDEX idx_lookup(region_code, locality_name),
  CONSTRAINT fk_food_landmarks_region FOREIGN KEY (region_code) REFERENCES regions(code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `event_landmarks` (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  region_code CHAR(2) NOT NULL,
  locality_name VARCHAR(50) NOT NULL,
  title VARCHAR(120) NOT NULL,
  description VARCHAR(255) NOT NULL,
  latitude DECIMAL(10,6) NULL,
  longitude DECIMAL(10,6) NULL,
  location_url VARCHAR(500) NOT NULL,
  source_name VARCHAR(100) NOT NULL,
  INDEX idx_lookup(region_code, locality_name),
  CONSTRAINT fk_event_landmarks_region FOREIGN KEY (region_code) REFERENCES regions(code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- app.py의 회원가입/로그인 기능이 사용하는 테이블 (app.py가 처음 요청 시 자동 생성하지만, 여기 포함해 미리 만들 수 있게 함)
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

-- 방문 기록 기능이 사용하는 테이블 (visits.py가 조회·저장 시 자동 생성할 예정, 여기 포함해 미리 만들 수 있게 함)
-- member_id, landmark_id는 members/장소 테이블에 대한 논리적 참조이며 DB 외래키는 선언하지 않음 (db erd.md 참고)
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

-- 즐겨찾기 기능이 사용하는 테이블 (favorites.py가 조회·저장 시 자동 생성할 예정, 여기 포함해 미리 만들 수 있게 함)
-- member_id, landmark_id는 members/장소 테이블에 대한 논리적 참조이며 DB 외래키는 선언하지 않음 (db erd.md 참고)
CREATE TABLE IF NOT EXISTS member_favorites (
  member_id BIGINT UNSIGNED NOT NULL,
  category VARCHAR(10) NOT NULL,
  landmark_id BIGINT UNSIGNED NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (member_id, category, landmark_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
