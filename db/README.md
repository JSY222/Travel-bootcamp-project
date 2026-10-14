# db: DB 자료 모음

DB 관련 SQL을 한곳에 모은 폴더입니다. 과거에는 루트와 `Travel-bootcamp-project/` 하위에도 같은 파일들이 중복으로 있었으나 정리했고, 이제 DB 자료는 이 폴더가 유일한 위치입니다.

| 폴더 | 내용 | DB / 표 구조 | 상태 |
| --- | --- | --- | --- |
| `current/` | `00_schema.sql`(테이블 구조만), `cityname_landmarks_1013.sql`(구조+샘플 데이터, 기존 테이블 DROP 후 재생성), `02_localities_geo_admin_codes.sql` | `cityname` DB: `regions`, `localities`, `geo_admin_codes`, `tourist_landmarks`, `food_landmarks`, `event_landmarks` | **현재 `app.py`가 쓰는 구조** |
| `cityname_split/` | `00`-`05` 분리 SQL과 `README.txt` | `cityname` DB: `regions`, `tourist_attractions`, `restaurants`, `events` 등 7개 표와 뷰 | 이전 구조 (약 1만 건 규모), 참고용 보관 |
| `legacy/` | `korea_travel_mariadb.sql` | `travel_landmarks` DB, `landmarks` 표 | 초기 덤프, 사용 안 함 |
| `backups/` | DB 마이그레이션 전 `mysqldump` 백업 | - | git에는 커밋하지 않음(.gitignore) |
| `members.sql` | `members` 테이블만 생성 | `cityname` DB: `members` | CREATE 권한 없는 환경용 fallback (`docs/member-auth.md` 참고) |

## 주의
- 새 환경을 처음 세팅할 때는 `current/00_schema.sql`(구조만, 데이터 없음)을 먼저 실행하세요.
- `current/cityname_landmarks_1013.sql`은 **`cityname` DB의 모든 일반 테이블을 DROP**한 뒤 새로 만들고 샘플 데이터까지 채웁니다. 실행 전에 백업하세요.
- `current/`와 `cityname_split/`은 같은 `cityname` DB를 대상으로 하지만 표 구조가 서로 다릅니다. 둘을 같은 DB에 섞어 넣지 마세요.
