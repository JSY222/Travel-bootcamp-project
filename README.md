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
| 🧭 | **단계별 지역 선택** | 지도에서 시·도 → 시·군·구 순서로 지역 선택 |
| 🏷️ | **카테고리별 표시** | 선택한 지역의 랜드마크를 관광지 · 맛집 · 행사로 구분 |
| 📍 | **마커 & 상세 정보** | 마커 클릭 시 상세 정보 팝업, 목록 카드 제공 |

<!-- 기능별 스크린샷을 넣어보세요 -->
<!--
<p align="center">
  <img src="docs/images/select-region.png" width="32%">
  <img src="docs/images/category.png" width="32%">
  <img src="docs/images/popup.png" width="32%">
</p>
-->

**🚀 향후 계획**

- [ ] 🔐 로그인
- [ ] ✅ 방문 인증과 스탬프
- [ ] ⭐ 리뷰 기능

<br>

## 🛠️ 기술 스택

| 구분 | 사용 기술 |
|:-:|---|
| ⚙️ **백엔드** | ![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![Flask](https://img.shields.io/badge/Flask-000000?style=flat-square&logo=flask&logoColor=white) ![PyMySQL](https://img.shields.io/badge/PyMySQL-4479A1?style=flat-square&logo=mysql&logoColor=white) |
| 🗄️ **DB** | ![MariaDB](https://img.shields.io/badge/MariaDB-003545?style=flat-square&logo=mariadb&logoColor=white) |
| 🎨 **프론트엔드** | ![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white) ![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white) ![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black) ![Leaflet](https://img.shields.io/badge/Leaflet-199900?style=flat-square&logo=leaflet&logoColor=white) |
| 🌏 **지도** | ![OpenStreetMap](https://img.shields.io/badge/OpenStreetMap-7EBC6F?style=flat-square&logo=openstreetmap&logoColor=white) 공개 행정구역 GeoJSON ([kr-admin-geojson](https://github.com/KnellBalm/kr-admin-geojson)) |

<br>

## ▶️ 실행 방법

**1️⃣ 저장소를 받고 패키지를 설치합니다.**

```bash
git clone https://github.com/JSY222/Travel-bootcamp-project.git
cd Travel-bootcamp-project
pip install -r requirements.txt
```

**2️⃣ 프로젝트 루트에 `.env` 파일을 만들어 DB 접속 정보를 적습니다.**
이 파일은 `.gitignore`에 포함되어 저장소에 올라가지 않습니다.

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=사용자명
DB_PASSWORD=비밀번호
```

**3️⃣ `db/` 폴더의 SQL로 DB를 준비합니다.**
자세한 내용은 [db/README.md](https://github.com/JSY222/Travel-bootcamp-project/blob/main/db/README.md)를 참고하세요.

**4️⃣ 서버를 실행하고 브라우저에서 `http://127.0.0.1:5000`을 엽니다.**

```bash
python app.py
```

> [!NOTE]
> DB 접속 정보 같은 비밀값은 코드에 직접 쓰지 않고 환경변수로 받습니다.

> [!WARNING]
> DB 준비용 SQL은 기존 테이블을 삭제하고 새로 만들 수 있으니, 실행 전에 백업하세요.

<br>

## 📁 폴더 구조

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

<br>

## 👥 팀

부트캠프 웹 프로젝트 1 팀

| 장시영 | 김재환 | 조성준 | 양재덕 |
|:-:|:-:|:-:|:-:|
| 역할<br><a href=""><img src="docs/images/readme/github.svg" alt="GitHub" width="20" height="20"></a> <a href=""><img src="docs/images/readme/globe.svg" alt="웹페이지" width="20" height="20"></a> | 역할<br><a href=""><img src="docs/images/readme/github.svg" alt="GitHub" width="20" height="20"></a> <a href=""><img src="docs/images/readme/globe.svg" alt="웹페이지" width="20" height="20"></a> | 역할<br><a href=""><img src="docs/images/readme/github.svg" alt="GitHub" width="20" height="20"></a> <a href=""><img src="docs/images/readme/globe.svg" alt="웹페이지" width="20" height="20"></a> | 역할<br><a href="https://github.com/YangJaeDeok"><img src="docs/images/readme/github.svg" alt="GitHub" width="20" height="20"></a> <a href="https://velog.io/@l0v3sick"><img src="docs/images/readme/velog.svg" alt="Velog" width="20" height="20"></a> <a href="https://www.linkedin.com/in/yangjaedeok/"><img src="docs/images/readme/linkedin.svg" alt="LinkedIn" width="20" height="20"></a> |

<br>

<div align="center">

Made with ❤️ by Cityname Team

</div>
