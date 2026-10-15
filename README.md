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
