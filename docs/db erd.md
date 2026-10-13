
erDiagram
    direction TB

    regions ||--o{ localities : "region_code"
    localities ||--o{ geo_admin_codes : "locality_id"

    regions ||--o{ tourist_landmarks : "region_code"
    regions ||--o{ food_landmarks : "region_code"
    regions ||--o{ event_landmarks : "region_code"

    localities ||--o{ tourist_landmarks : "region_code + locality_id"
    localities ||--o{ food_landmarks : "region_code + locality_id"
    localities ||--o{ event_landmarks : "region_code + locality_id"

    regions {
        char_2 code PK
        varchar name
        enum region_type
        tinyint display_order
    }

    localities {
        int id PK
        char_2 region_code FK
        varchar name
        enum locality_type
    }

    geo_admin_codes {
        enum source_level PK
        varchar source_code PK
        int locality_id FK
    }

    tourist_landmarks {
        int id PK
        char_2 region_code FK
        int locality_id FK
        varchar locality_name
        varchar title
        varchar description
        decimal latitude
        decimal longitude
        varchar location_url
        varchar source_name
    }

    food_landmarks {
        int id PK
        char_2 region_code FK
        int locality_id FK
        varchar locality_name
        varchar title
        varchar description
        decimal latitude
        decimal longitude
        varchar location_url
        varchar source_name
    }

    event_landmarks {
        int id PK
        char_2 region_code FK
        int locality_id FK
        varchar locality_name
        varchar title
        varchar description
        decimal latitude
        decimal longitude
        varchar location_url
        varchar source_name
    }
