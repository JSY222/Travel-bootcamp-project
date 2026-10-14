# db: DB 자료 모음

DB 관련 SQL을 한곳에 모은 폴더입니다. 과거에는 루트와 `Travel-bootcamp-project/` 하위에도 같은 파일들이 중복으로 있었으나 정리했고, 이제 DB 자료는 이 폴더가 유일한 위치입니다.

| 폴더 | 내용 | DB / 표 구조 | 상태 |
| --- | --- | --- | --- |
| `current/` | `00_schema.sql`(테이블 구조만), `cityname_landmarks_1013.sql`(구조+샘플 데이터, 기존 테이블 DROP 후 재생성), `initialize_missing_cityname.sql`, `01~07_*_temp.sql`(테이블별 순서 실행용 임시 검증 파일, 확정되면 삭제 예정) | `cityname` DB: `regions`, `localities`, `geo_admin_codes`, `tourist_landmarks`, `food_landmarks`, `event_landmarks`, `members` | **현재 `app.py`가 쓰는 구조** |
| `cityname_split/` | `00`-`05` 분리 SQL과 `README.txt` | `cityname` DB: `regions`, `tourist_attractions`, `restaurants`, `events` 등 7개 표와 뷰 | 이전 구조 (약 1만 건 규모), 참고용 보관 |
| `legacy/` | `korea_travel_mariadb.sql` | `travel_landmarks` DB, `landmarks` 표 | 초기 덤프, 사용 안 함 |
| `data/datalab_food_top20/` | 데이터랩 공식 지역 맛집 ZIP | 지역별 전체 순위 중 1~20위 + TourAPI 보강 | 수집·검증 진행 중 |
| `backups/` | DB 마이그레이션 전 `mysqldump` 백업 | - | git에는 커밋하지 않음(.gitignore) |
| `members.sql` | `members` 테이블만 생성 | `cityname` DB: `members` | CREATE 권한 없는 환경용 fallback (`docs/member-auth.md` 참고) |

## 주의
- 새 환경을 처음 세팅할 때는 `current/00_schema.sql`(구조만, 데이터 없음)을 먼저 실행하세요.
- `current/cityname_landmarks_1013.sql`은 **`cityname` DB의 모든 일반 테이블을 DROP**한 뒤 새로 만들고 샘플 데이터까지 채웁니다. 실행 전에 백업하세요.
- `current/`와 `cityname_split/`은 같은 `cityname` DB를 대상으로 하지만 표 구조가 서로 다릅니다. 둘을 같은 DB에 섞어 넣지 마세요.
- 맛집 순위 교체는 `import_datalab_food_top20.py`의 기본 DRY RUN으로 먼저 검증하세요. 현재 확보된 공식 파일만 남기고 미수집 지역을 비우려면 `--allow-partial --replace-all --apply`를 사용합니다.
- **한글 데이터가 있는 SQL 파일은 맨 앞에 `SET NAMES utf8mb4;`를 넣으세요.** 이 서버의 `mysql` 클라이언트 기본 연결 문자셋이 `latin1`이라, 이 구문 없이 `mysql cityname < file.sql`로 한글 INSERT를 실행하면 글자가 이중 인코딩되어 깨집니다(터미널에서 `mysql`로 다시 조회하면 같은 방식으로 깨짐이 상쇄되어 겉보기엔 정상처럼 보이는 함정이 있음 — `pymysql`(`charset='utf8mb4'`)로 열어보면 깨진 게 보입니다). `00_schema.sql`과 `01~07_*_temp.sql`은 이미 파일 맨 앞에 `SET NAMES utf8mb4;`를 넣어뒀기 때문에 플래그 없이 `mysql cityname < file.sql`로 실행해도 안전합니다. 새 SQL 파일을 추가할 때도 이 패턴을 따르세요.
