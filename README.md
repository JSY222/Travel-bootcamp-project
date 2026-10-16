<div align="center">

# 🗺️ Cityname

### 국내 여행 지도

**지도에서 지역을 고르고, 그 지역의 관광지 · 맛집 · 행사를 한눈에**

<br>

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![MariaDB](https://img.shields.io/badge/MariaDB-003545?style=for-the-badge&logo=mariadb&logoColor=white)
![Leaflet](https://img.shields.io/badge/Leaflet-199900?style=for-the-badge&logo=leaflet&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)

<br>

<!-- 대표 이미지 / 데모 GIF를 여기에 넣어주세요 -->
<!-- <img src="docs/images/main.png" alt="Cityname 메인 화면" width="800"> -->

</div>

<br>

## 📌 프로젝트 소개

> 부트캠프 웹 프로젝트 1 (**Travel Info and Course Web**) 팀 프로젝트입니다.

여행 정보를 찾을 때 **지도 앱은 정보가 너무 많고**, **블로그는 정보가 흩어져 있다**는 문제의식에서 출발했습니다.

큰 지도에서 시·도와 시·군·구를 차례로 선택하면 해당 지역의 랜드마크를 **한 화면**에서 볼 수 있습니다.
길 찾기 대신 **"어디를 갈지 고르는 일"** 에 집중합니다.

<br>

## ✨ 주요 기능

| | 기능 | 설명 |
|:-:|---|---|
| 🧭 | **단계별 지역 탐색** | 대한민국 지도에서 시·도 → 시·군·구 순서로 이동하고 이전 단계로 돌아가기 |
| 🏷️ | **여행 정보 분류** | 선택한 지역의 관광지 · 맛집 · 행사를 카테고리별 목록과 지도 마커로 표시 |
| 🍽️ | **지역 맛집 랭킹** | 한국관광 데이터랩 기반 TOP 20을 전체 · 현지인 · 외지인 기준으로 조회 |
| 📍 | **장소 상세 정보** | 장소 설명, 위치, 출처와 외부 위치 링크를 팝업 및 카드에서 확인 |
| 🔐 | **회원 기능** | CSRF 보호가 적용된 회원가입 · 로그인 · 로그아웃과 개인 프로필 관리 |
| 🧠 | **맞춤 장소 추천** | 프로필의 MBTI와 여행 스타일을 바탕으로 관광지 · 맛집 · 행사를 추천 |
| ♡ | **여행서랍과 즐겨찾기** | 현재 탐색 중인 장소를 임시 여행서랍에 담고, 로그인 후 즐겨찾기로 일괄 저장 |
| 📷 | **방문 기록** | 방문 날짜, 후기, 사진을 장소별로 등록하고 나의 방문 내역에서 확인 |
| 🏅 | **스탬프와 랭킹** | 방문 범위에 따라 흰색 · 은색 · 금색 스탬프를 발급하고 회원별 순위와 도감을 제공 |
| 💰 | **포인트 내역** | 스탬프 보상 포인트, 날짜별 차감 상태, 지역·기간 필터와 페이지별 내역을 제공 |

<!-- 기능별 스크린샷을 넣어보세요 -->
<!--
<p align="center">
  <img src="docs/images/select-region.png" width="32%">
  <img src="docs/images/category.png" width="32%">
  <img src="docs/images/popup.png" width="32%">
</p>
-->

## 🛠️ 기술 스택

| 구분 | 사용 기술 |
|:-:|---|
| ⚙️ **백엔드** | ![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![Flask](https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white) ![PyMySQL](https://img.shields.io/badge/PyMySQL-4479A1?style=flat-square&logo=mysql&logoColor=white) |
| 🗄️ **DB** | ![MariaDB](https://img.shields.io/badge/MariaDB-003545?style=flat-square&logo=mariadb&logoColor=white) |
| 🎨 **프론트엔드** | ![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white) ![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white) ![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black) ![Leaflet](https://img.shields.io/badge/Leaflet-199900?style=flat-square&logo=leaflet&logoColor=white) |
| 🌏 **지도** | ![OpenStreetMap](https://img.shields.io/badge/OpenStreetMap-7EBC6F?style=flat-square&logo=openstreetmap&logoColor=white) 공개 행정구역 GeoJSON ([kr-admin-geojson](https://github.com/KnellBalm/kr-admin-geojson)) |

<br>

## ▶️ 실행 방법

### 1. 저장소와 Python 환경 준비

Python 3와 MariaDB가 설치되어 있어야 합니다. 아래 명령은 Windows PowerShell 기준입니다.

```powershell
git clone https://github.com/JSY222/Travel-bootcamp-project.git
cd Travel-bootcamp-project
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2. 환경변수 설정

프로젝트 루트에 `.env` 파일을 만들고 MariaDB 접속 정보를 입력합니다. `.env`는 Git에 포함되지 않습니다.

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=MariaDB_비밀번호
SECRET_KEY=충분히_긴_임의의_문자열
```

> 앱이 사용하는 데이터베이스 이름은 현재 `cityname`으로 고정되어 있습니다. 운영 또는 팀 공용 DB에서는 안정적인 `SECRET_KEY`를 반드시 설정하세요.

### 3. 데이터베이스 준비

이미 팀에서 사용 중인 `cityname` DB가 있다면 데이터를 초기화하지 말고 필요한 마이그레이션만 적용하세요. 새 로컬 환경에서 샘플 데이터로 시작하려면 다음 순서로 준비합니다.

```powershell
# 주의: 아래 첫 SQL은 cityname의 기존 일반 테이블을 삭제하고 샘플 데이터로 다시 만듭니다.
mariadb -u root -p < db/current/cityname_landmarks_1013.sql

# 회원, 방문 기록, 즐겨찾기 테이블과 현재 컬럼을 준비합니다.
mariadb -u root -p cityname < db/members.sql
mariadb -u root -p < db/migrations/20261015_member_mbti.sql
mariadb -u root -p cityname < db/member_visits.sql
mariadb -u root -p cityname < db/member_favorites.sql

# 스탬프 보상 테이블과 기존 방문 기록의 포인트를 준비합니다.
python db/migrate_stamp_rewards.py

# 선택: 한국관광 데이터랩 맛집 TOP 20을 추가합니다.
python db/apply_datalab_food_sql.py
```

MariaDB 설치 환경에 따라 `mariadb` 대신 `mysql` 명령을 사용해야 할 수 있습니다. 빈 DB를 직접 구성하거나 기존 데이터를 이전하는 방법은 [db/README.md](db/README.md)를 참고하세요.

### 4. 서버 실행

```powershell
python app.py
```

브라우저에서 [http://127.0.0.1:5000](http://127.0.0.1:5000)을 엽니다.

### 5. 테스트 실행

```powershell
python -m unittest discover -s tests -v
```

> [!WARNING]
> `db/current/cityname_landmarks_1013.sql`과 일부 마이그레이션은 기존 테이블이나 데이터를 변경합니다. 기존 DB에 적용하기 전 반드시 백업하고 [DB 안내](db/README.md)의 주의사항을 확인하세요.

<br>

## 📁 폴더 구조

```
.
├── app.py                 Flask 서버와 기능별 API
├── templates/             화면별 HTML 템플릿
├── static/                CSS, JavaScript, 이미지
├── db/                    DB 스키마와 초기 데이터
├── docs/                  프로젝트 문서
├── requirements.txt       Python 패키지 목록
└── README.md
```

위 구조는 웹 실행과 사용자 기능 구현에 직접 연결되는 큰 구성만 표시합니다. 세부 기능 모듈, 테스트, 데이터 생성 도구와 이전 자료는 생략했습니다.

<br>

## ©️ 저작권 및 출처 안내

저작권법 제24조의2(공공저작물의 자유이용)에 따라 한국관광공사에서 저작재산권의 전부를 보유하고 있거나 자유이용허락표시에 대한 권리자의 동의를 받은 경우는 **공공저작물 자유이용허락표시기준(공공누리, KOGL)** 을 부착하여 별도의 이용허락 없이 자유이용이 가능합니다.

### 데이터 및 이미지 출처

- [한국관광공사](https://knto.or.kr/)
- [공공데이터포털](https://www.data.go.kr/)
- [한국관광데이터랩](https://datalab.visitkorea.or.kr/)

프로젝트에서 사용한 관광지·맛집·행사 데이터와 관련 이미지는 위 기관에서 제공한 자료를 바탕으로 하며, 개별 자료에 표시된 공공누리 유형과 이용조건을 따릅니다.

### 공공누리 유형별 이용조건

| 유형 | 공공누리 표시 |
|:-:|:-:|
| **제0유형** | [<img src="docs/images/readme/img_open01.png" alt="만료 저작물 유형(제0유형)">](https://knto.or.kr/humanframe/theme/kto/assets/image/content/img_open01.png) |
| **제1유형** | [<img src="docs/images/readme/img_open02.png" alt="공공누리 제1유형">](https://knto.or.kr/humanframe/theme/kto/assets/image/content/img_open02.png) |
| **제2유형** | [<img src="docs/images/readme/img_open03.png" alt="공공누리 제2유형">](https://knto.or.kr/humanframe/theme/kto/assets/image/content/img_open03.png) |
| **제3유형** | [<img src="docs/images/readme/img_open04.png" alt="공공누리 제3유형">](https://knto.or.kr/humanframe/theme/kto/assets/image/content/img_open04.png) |
| **제4유형** | [<img src="docs/images/readme/img_open05.png" alt="공공누리 제4유형">](https://knto.or.kr/humanframe/theme/kto/assets/image/content/img_open05.png) |
| **AI유형**<br>\* 하단 이용조건 필수 확인 | [<img src="docs/images/readme/img_open06.png" alt="공공누리 AI유형">](https://knto.or.kr/humanframe/theme/kto/assets/image/content/img_open06.png) |

> [!IMPORTANT]
> 공공누리가 부착된 공공저작물은 제1유형의 경우 출처표시만 하면 자유이용이 가능합니다. 제2유형은 상업적 이용을, 제3유형은 변경 이용을, 제4유형은 상업적 이용과 변경 이용을 금지하므로 반드시 이용조건을 확인한 후 허용 범위 안에서 이용해야 합니다.

또한 제1유형을 포함하여 어느 유형이든 출처를 반드시 표시해야 합니다. 출처에는 **발행연도, 해당 공공기관명과 홈페이지 URL**, 저작물 작성자의 성명이 표시된 경우에는 **작성자 성명**도 포함해야 합니다.

**출처 표시 예시**

> 본 저작물은 ‘한국관광공사’에서 ‘2022년’ 작성하여 공공누리 제1유형으로 개방한 ‘저작물명(저작권자: 홍길동)’을 이용하였으며, 해당 저작물은 ‘한국관광공사, kto.visitkorea.or.kr’에서 무료로 내려받으실 수 있습니다.

<br>

## 👥 팀

부트캠프 웹 프로젝트 1 팀

| 장시영 | 김재환 | 조성준 | 양재덕 |
|:-:|:-:|:-:|:-:|
| 역할<br><a href="https://github.com/JSY222/"><img src="docs/images/readme/github.svg" alt="GitHub" width="20" height="20"></a> <a href="https://blog.naver.com/wkdtldud2621"><img src="docs/images/readme/naver.svg" alt="네이버 블로그" width="20" height="20"></a> | 역할<br><a href=""><img src="docs/images/readme/github.svg" alt="GitHub" width="20" height="20"></a> <a href=""><img src="docs/images/readme/globe.svg" alt="웹페이지" width="20" height="20"></a> | 역할<br><a href=""><img src="docs/images/readme/github.svg" alt="GitHub" width="20" height="20"></a> <a href=""><img src="docs/images/readme/globe.svg" alt="웹페이지" width="20" height="20"></a> | 역할<br><a href="https://github.com/YangJaeDeok"><img src="docs/images/readme/github.svg" alt="GitHub" width="20" height="20"></a> <a href="https://velog.io/@l0v3sick"><img src="docs/images/readme/velog.svg" alt="Velog" width="20" height="20"></a> <a href="https://www.linkedin.com/in/yangjaedeok/"><img src="docs/images/readme/linkedin.svg" alt="LinkedIn" width="20" height="20"></a> |

<br>

<div align="center">

Made with ❤️ by Cityname Team

</div>
