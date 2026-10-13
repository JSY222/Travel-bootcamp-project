# Cityname: 국내 여행 지도

지도에서 지역을 고르고 그 지역의 관광지, 맛집, 행사 정보를 확인하는 국내 여행 정보 웹 서비스입니다. 부트캠프 웹 프로젝트 1(Travel Info and Course Web) 팀 프로젝트입니다.

## 프로젝트 소개

여행 정보를 찾을 때 지도 앱은 정보가 너무 많고, 블로그는 정보가 흩어져 있다는 문제의식에서 출발했습니다. 큰 지도에서 시·도와 시·군·구를 차례로 선택하면 해당 지역의 랜드마크를 한 화면에서 볼 수 있습니다. 길 찾기 대신 어디를 갈지 고르는 데 집중합니다.

## 주요 기능

- 지도에서 시·도, 시·군·구 순서로 지역 선택
- 선택한 지역의 랜드마크를 카테고리(관광지, 맛집, 행사)별로 표시
- 마커 클릭 시 상세 정보 팝업, 목록 카드 제공

향후 로그인, 방문 인증과 스탬프, 리뷰 기능을 추가할 계획입니다.

## 기술 스택

| 구분 | 사용 기술 |
| --- | --- |
| 백엔드 | Python, Flask, PyMySQL |
| DB | MariaDB |
| 프론트엔드 | HTML, CSS, JavaScript, Leaflet |
| 지도 | OpenStreetMap, 공개 행정구역 GeoJSON ([kr-admin-geojson](https://github.com/KnellBalm/kr-admin-geojson)) |

## 실행 방법

1. 저장소를 받고 패키지를 설치합니다.
   ```bash
   git clone https://github.com/JSY222/Travel-bootcamp-project.git
   cd Travel-bootcamp-project
   pip install -r requirements.txt
   ```
2. 프로젝트 루트에 `.env` 파일을 만들어 DB 접속 정보를 적습니다. 이 파일은 `.gitignore`에 포함되어 저장소에 올라가지 않습니다.
   ```
   DB_HOST=127.0.0.1
   DB_PORT=3306
   DB_USER=사용자명
   DB_PASSWORD=비밀번호
   ```
3. `db/` 폴더의 SQL로 DB를 준비합니다. 자세한 내용은 [db/README.md](db/README.md)를 참고하세요.
4. 서버를 실행하고 브라우저에서 `http://127.0.0.1:5000`을 엽니다.
   ```bash
   python app.py
   ```

> DB 접속 정보 같은 비밀값은 코드에 직접 쓰지 않고 환경변수로 받습니다.
> DB 준비용 SQL은 기존 테이블을 삭제하고 새로 만들 수 있으니, 실행 전에 백업하세요.

## 폴더 구조

```
.
├── app.py                 Flask 서버와 API
├── templates/             HTML 템플릿
├── static/                CSS, JavaScript
├── db/                    DB 관련 SQL과 설명
├── docs/                  프로젝트 문서
├── requirements.txt       Python 패키지 목록
└── README.md
```

## 팀

부트캠프 웹 프로젝트 1 팀: 장시영, 김재환, 조성준, 양재덕
