# cityname ERD

2026-10-14 기준, 로컬 MariaDB의 information_schema에서 실제 테이블·컬럼·외래키를 읽어 작성했습니다. DB 데이터와 웹 기능은 변경하지 않았습니다.

일반 테이블 6개, 뷰 3개입니다. 아래 ERD는 일반 테이블 전체 컬럼과 실제 외래키 관계를 표시합니다. PK는 기본키, FK는 외래키이며 모든 컬럼은 NOT NULL입니다.

```mermaid
erDiagram
    direction TB

    regions ||--o{ event_landmarks : "region_code"
    localities ||--o{ event_landmarks : "region_code + locality_id"
    regions ||--o{ food_landmarks : "region_code"
    localities ||--o{ food_landmarks : "region_code + locality_id"
    localities ||--o{ geo_admin_codes : "locality_id"
    regions ||--o{ localities : "region_code"
    regions ||--o{ tourist_landmarks : "region_code"
    localities ||--o{ tourist_landmarks : "region_code + locality_id"

    tourist_landmarks {
        int id PK "int(10) unsigned"
        char region_code FK "char(2)"
        varchar locality_name "varchar(50)"
        varchar title "varchar(120)"
        varchar description "varchar(255)"
        decimal latitude "decimal(10,6)"
        decimal longitude "decimal(10,6)"
        varchar location_url "varchar(500)"
        varchar source_name "varchar(100)"
        int locality_id FK "int(10) unsigned"
    }

    regions {
        char code PK "char(2)"
        varchar name "varchar(50)"
        enum region_type "enum('province','metro')"
        tinyint display_order "tinyint(3) unsigned"
    }

    localities {
        int id PK "int(10) unsigned"
        char region_code FK "char(2)"
        varchar name "varchar(50)"
        enum locality_type "enum('city','county','district','town','other')"
    }

    geo_admin_codes {
        enum source_level PK "enum('SIG','EMD')"
        varchar source_code PK "varchar(10)"
        int locality_id FK "int(10) unsigned"
    }

    food_landmarks {
        int id PK "int(10) unsigned"
        char region_code FK "char(2)"
        varchar locality_name "varchar(50)"
        varchar title "varchar(120)"
        varchar description "varchar(255)"
        decimal latitude "decimal(10,6)"
        decimal longitude "decimal(10,6)"
        varchar location_url "varchar(500)"
        varchar source_name "varchar(100)"
        int locality_id FK "int(10) unsigned"
    }

    event_landmarks {
        int id PK "int(10) unsigned"
        char region_code FK "char(2)"
        varchar locality_name "varchar(50)"
        varchar title "varchar(120)"
        varchar description "varchar(255)"
        decimal latitude "decimal(10,6)"
        decimal longitude "decimal(10,6)"
        varchar location_url "varchar(500)"
        varchar source_name "varchar(100)"
        int locality_id FK "int(10) unsigned"
    }
```

관광지·맛집·행사의 `region_code`는 `regions.code`를 참조합니다. `(region_code, locality_id)`는 `localities.(region_code, id)`를 참조하는 복합 외래키입니다. `geo_admin_codes`의 기본키는 `(source_level, source_code)`입니다.

뷰는 `v_all_places`, `v_landmarks`, `v_landmark_counts`입니다. 뷰는 별도 데이터 저장 테이블이 아니므로 위 테이블 ERD에서 제외했습니다.
