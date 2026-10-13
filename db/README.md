# db: DB 자료 모음

DB 관련 SQL을 한곳에 모은 폴더입니다. 루트의 기존 파일은 그대로 두고 복제본만 여기에 있습니다.

| 폴더 | 내용 | DB / 표 구조 | 상태 |
| --- | --- | --- | --- |
| `current/` | `cityname_landmarks_1013.sql` (루트 `1013_1sql.txt`를 `.sql`로 바꿔 복제) | `cityname` DB: `regions`, `tourist_landmarks`, `food_landmarks`, `event_landmarks` | **현재 `app.py`가 쓰는 구조** |
| `cityname_split/` | `00`-`05` 분리 SQL과 `README.txt` | `cityname` DB: `regions`, `tourist_attractions`, `restaurants`, `events` 등 7개 표와 뷰 | 이전 구조 (약 1만 건 규모) |
| `legacy/` | `korea_travel_mariadb.sql` | `travel_landmarks` DB, `landmarks` 표 | 초기 덤프, 사용 안 함 |

## 주의
- `current/cityname_landmarks_1013.sql`은 **`cityname` DB의 모든 일반 테이블을 DROP**한 뒤 새로 만듭니다. 실행 전에 백업하세요.
- `current/`와 `cityname_split/`은 같은 `cityname` DB를 대상으로 하지만 표 구조가 서로 다릅니다. 둘을 같은 DB에 섞어 넣지 마세요.
- `legacy/korea_travel_mariadb.sql`은 루트와 `Travel-bootcamp-project/` 하위에 있던 중복 파일 중 하나입니다. 두 파일은 줄바꿈(CRLF/LF)만 다르고 내용이 같습니다.
