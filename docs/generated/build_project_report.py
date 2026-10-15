"""Generate a Korean PDF from inspected source and the read-only DB snapshot."""
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Circle, Polygon
from reportlab.graphics import renderPM

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
snapshot = json.loads((OUT / 'schema_snapshot.json').read_text(encoding='utf-8'))
pdfmetrics.registerFont(TTFont('Korean', 'C:/Windows/Fonts/malgun.ttf'))
pdfmetrics.registerFont(TTFont('KoreanBold', 'C:/Windows/Fonts/malgunbd.ttf'))
pdfmetrics.registerFontFamily('Korean', normal='Korean', bold='KoreanBold')
styles = getSampleStyleSheet()
for name in ['Normal', 'BodyText', 'Heading1', 'Heading2', 'Title']:
    styles[name].fontName = 'Korean'
    styles[name].wordWrap = 'CJK'
styles.add(ParagraphStyle(name='BodyKR', fontName='Korean', fontSize=9, leading=15, spaceAfter=8, wordWrap='CJK'))
styles.add(ParagraphStyle(name='SmallKR', fontName='Korean', fontSize=7.5, leading=12, wordWrap='CJK'))
styles.add(ParagraphStyle(name='CaptionKR', fontName='Korean', fontSize=8, leading=13, textColor=colors.HexColor('#6e8076'), spaceAfter=12))
styles['Heading1'].fontName='KoreanBold'; styles['Heading1'].fontSize=19; styles['Heading1'].leading=27
styles['Heading2'].fontName='KoreanBold'; styles['Heading2'].fontSize=12; styles['Heading2'].leading=19
story=[]
GREEN=colors.HexColor('#466b55'); LIGHT=colors.HexColor('#edf3e8'); GRAY=colors.HexColor('#73867a')

def para(text,style='BodyKR'):
    return Paragraph(text,styles[style])
def add(text): story.append(para(text))
def heading(text): story.append(para(text,'Heading1'));story.append(Spacer(1,10))
def sub(text): story.append(para(text,'Heading2'))
def page(title): story.append(PageBreak());heading(title)
def table(headers,rows,widths=None):
    values=[[para(escape(str(v)),'SmallKR') for v in row] for row in [headers]+rows]
    t=Table(values,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),LIGHT),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#d1ddcf')),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    story.append(t);story.append(Spacer(1,12))
def box(d,x,y,w,h,title,lines=(),fill=LIGHT):
    d.add(Rect(x,y,w,h,rx=8,ry=8,fillColor=fill,strokeColor=colors.HexColor('#b9ccbc'),strokeWidth=1))
    d.add(String(x+10,y+h-19,title,fontName='KoreanBold',fontSize=9,fillColor=GREEN))
    for i,line in enumerate(lines):d.add(String(x+10,y+h-36-i*13,line,fontName='Korean',fontSize=7.3,fillColor=colors.HexColor('#52665a')))
def edge(d,x1,y1,x2,y2,label='',dashed=False):
    d.add(Line(x1,y1,x2,y2,strokeColor=GRAY,strokeWidth=1,strokeDashArray=[4,3] if dashed else None))
    dx=x2-x1;dy=y2-y1
    import math
    n=math.hypot(dx,dy) or 1;ux=dx/n;uy=dy/n
    d.add(Polygon([x2,y2,x2-ux*6-uy*3,y2-uy*6+ux*3,x2-ux*6+uy*3,y2-uy*6-ux*3],fillColor=GRAY,strokeColor=None))
    if label:d.add(String((x1+x2)/2+3,(y1+y2)/2+4,label,fontName='Korean',fontSize=7,fillColor=GRAY))
def figure(d,caption):story.append(d);story.append(para(caption,'CaptionKR'))

heading('여행서랍 · 구현 현황 및 설계 자료')
add('<b>변경사항 · 파일 연결관계 · 데이터 흐름 · DB ERD</b>')
add('작성 기준: 2026-10-15 / 현재 로컬 소스와 실제 cityname DB의 읽기 전용 조회 결과')
d=Drawing(500,235)
box(d,15,120,145,95,'여행을 발견하기',['전국·지역 검색과 분류','아이콘 태그 · 장소 정보','MBTI 기반 참고 추천'])
box(d,180,120,145,95,'여행을 기록하기',['사진·리뷰 → 흰색 스탬프','지역 정복 → 은색·금색','개인 프로필과 보관소'])
box(d,345,120,145,95,'여행을 모아보기',['임시 찜 → 일괄 즐겨찾기','종류별 TOP 5 랭킹','드래그 가능한 지도 패널'])
edge(d,160,165,180,165);edge(d,325,165,345,165)
box(d,80,15,340,65,'Flask + MariaDB + Leaflet',['서버 검증 · 세션 인증 · 지도 렌더링 · 원본 데이터'])
figure(d,'그림 1. 최종 서비스 기능 구성. 그림은 코드 기반 설명도이며 실제 브라우저 캡처가 아닙니다.')
sub('읽는 순서')
add('1. 최종 변경사항 → 2. 화면·파일 구조 → 3. 주요 기능 흐름 → 4. 실제 DB ERD → 5. 스키마·검증 및 제한사항')
add('비밀번호, SECRET_KEY, 개인정보 원문과 사진 원본은 포함하지 않습니다. 초기 퍼즐 실험 등 폐기된 구현은 현재 기능과 구분합니다.')

page('1. 지금까지 적용한 변경사항')
table(['영역','최종 동작'],[
('브랜드·인트로','Cityname 표시를 여행서랍으로 변경. 서랍 로고, 주아 글씨체, 통통 튀는 입체 글자와 광택. 3초 뒤 사라지고 구름이 걷히며 지도 공개.'),
('지도 탐색','초기 지도를 축소해 전국을 보기 쉽게 조정. 시·도 → 시·군·구 선택, 검색 결과로 이동. 선택 지역에서 분류 필터 가능.'),
('장소 표시','퍼즐 구조는 제거. 카메라·음식·행사 배지를 임의로 경계 안에 분산. 이름은 가로 5글자 후 ... 처리. 클릭하면 상세 정보와 사진·리뷰 작성.'),
('지역 워터마크','시·군·구 로고와 이름을 약 30% 크기로 연하게 표시. 경계 안에 들어가는 위치를 검색하고 필요하면 축소.'),
('패널 배치','흰색 패널 폭 450px. 장소 종류 → 지역 검색 → 전체 지역 펼치기 → 즐겨찾기 → 나에게 맞는 여행지 추천.'),
('지도 상자','로그인·랭킹·임시 찜 상자는 반투명. 배경을 잡아 이동, 입력·버튼은 개별 동작 유지. 우측 상단 이전 단계 버튼.'),
('랭킹','흰색·은색·금색별 최대 5명, 동점 공동 순위. 각 회원의 3종 보유/전체 수 표시. 설명 ? 버튼. 응원은 흰색 패널 아래 본인 순위에 맞춰 표시.'),
('스타일','점선 회전 효과는 제거. 평면 게임 메뉴 느낌, 테두리 선택 표시. 흰색·은색·금색 스탬프 SVG 통일.'),
],[92,408])

page('1-2. 계정·여행 기록·추천 변경사항')
table(['영역','동작과 저장'],[
('프로필','방문 도시·여행 기록·즐겨찾기·스탬프의 4개 카드. 사진과 후기 표시. 고운돋움, 크림·파스텔 색상. 상세 회원정보는 펼치기.'),
('회원정보 수정','아이디와 비밀번호는 수정 불가. 이름·생일·주소·여행 스타일·MBTI 수정 가능. 로그인·CSRF 검증 후 본인 행만 UPDATE.'),
('MBTI','회원가입과 수정에 영문자 4글자 입력. 대문자로 저장. 추천은 I/E 및 마지막 J/P 사용. 추천은 유효한 16종 형식만 허용.'),
('방문 기록','사진과 리뷰를 member_visits에 저장. 동일 회원+분류+장소는 갱신하여 중복 집계 방지. 사진은 DB BLOB이며 접근은 소유자만 가능.'),
('데이터랩 연결','좌표 없는 맛집도 사진·리뷰와 즐겨찾기 저장 가능. POI 앞 12자리 HEX로 별도 ID 범위 생성. 좌표를 DB에 임의로 넣지는 않음.'),
('임시 찜','sessionStorage의 travel-trip-tray. 현재 탭의 임시 목록. 새로고침 시 유지, 삭제·일괄 즐겨찾기 추가 가능. DB 영구 저장 아님.'),
('즐겨찾기','직접 저장과 찜 일괄 저장은 같은 테이블 사용. 버튼 아래 접는 목록. 지역 구분 없이 기본 5곳, 이후 더 펼치기. 자동 확대 없음.'),
('보관소','기존 도감 이름을 보관소로 변경. 방문한 장소 스탬프만 지역별 조회. 시·도·시군구 펼치기와 지역 완성 상태 표시.'),
('맞춤 추천','DB 이름·설명의 키워드 점수. I는 자연·산책, E는 축제·체험, J는 관람·계획, P는 자유 탐색. 종류별 최대 3곳. 찜·즐겨찾기 연결.'),
('시연 데이터','사용자 요청으로 기존 계정에 서울 데이터랩 맛집 무작위 20곳의 시연 기록 추가. 기존 계정 사진을 24×24 저용량 JPEG로 가공. 후기에는 시연임을 표시.'),
],[92,408])
add('변경 과정에서 사용했던 퍼즐과 전국 장소 전용 패널, 데이터랩 별도 선택 패널은 현재 메인 화면에서 제거됐습니다. DB와 관련 API 자체는 유지됩니다.')

page('2. 화면 구성과 파일 연결관계')
d=Drawing(500,380)
box(d,0,15,155,355,'왼쪽 흰색 패널',['여행서랍 / 이전 단계','랭킹 + ? 설명','스탬프 보관소','장소 종류 선택','지역 검색','전체 지역 펼치기','즐겨찾기 5곳 + 더보기','나에게 맞는 여행지 추천'])
box(d,170,15,330,355,'지도 영역',['Leaflet / 행정구역 GeoJSON','시군구 로고 + 지역명 워터마크','지역 경계 안 임의 장소 태그','장소 팝업 → 사진·리뷰 / 찜','상단 로그인 정보 / 이전 단계'])
box(d,185,35,125,75,'찜한 장소',['반투명 · 이동 가능','일괄 즐겨찾기 저장'])
box(d,325,35,160,75,'스탬프 랭킹',['반투명 · 이동 가능','개인 스탬프 펼치기'])
figure(d,'그림 2. 메인 화면 배치 설명도. 모바일에서는 화면 폭에 따라 배치가 달라집니다.')
table(['템플릿','연결 스크립트'],[
('templates/index.html','stamps.js, stamp-catalog.js, visits.js, favorites.js, trip-tray.js, recommendations.js, sidebar.js, account.js, map.js, draggable-panels.js'),
('templates/profile.html','account.js, profile.js / 서버가 회원정보와 지역 로고 JSON 전달'),
('templates/signup.html','account.js / 회원가입, 여행 스타일, MBTI 입력'),
('static/css/style.css','세 화면의 공통 스타일. 화면별 class 및 미디어쿼리로 분기.'),
],[145,355])

page('2-2. 서버·브라우저·DB 연결도')
d=Drawing(500,395)
box(d,0,275,150,105,'브라우저 스크립트',['map.js / account.js','visits.js / favorites.js','stamps.js / profile.js','trip-tray.js / 추천'])
box(d,190,275,130,105,'Flask app.py',['환경설정 / 인증','페이지 렌더링','지역·장소·추천 API'])
box(d,360,275,140,105,'기능 모듈',['visits.py','favorites.py','food_rankings.py','food_locations.py'])
edge(d,150,335,190,335,'HTTP');edge(d,320,335,360,335,'등록')
box(d,200,130,285,90,'MariaDB · cityname',['회원 / 방문 / 즐겨찾기','지역 / 관광지 / 맛집 / 행사','데이터랩 순위 + TOP20 뷰'])
edge(d,255,275,255,220,'PyMySQL');edge(d,435,275,435,220)
box(d,0,130,150,90,'브라우저 임시 저장',['sessionStorage','travel-trip-tray','DB와 별개인 찜 목록'])
edge(d,75,275,75,220,'찜')
box(d,0,10,220,75,'설정·준비 파일',['.env → dotenv → DB_CONFIG','requirements.txt / .venv'])
box(d,270,10,230,75,'데이터 준비 파일',['db/current + migrations','db/generated / data ZIP·CSV'])
edge(d,220,50,245,130);edge(d,390,85,390,130)
figure(d,'그림 3. 실행 중 연결관계. SQL·CSV는 준비 자료이며 메인 웹이 자동으로 매번 가져오는 파일이 아닙니다.')
table(['Python 파일','책임'],[
('app.py','Flask 시작, 회원 인증·수정, 화면 렌더링, 지역·장소·추천, 로고 메타데이터'),
('visits.py','사진·리뷰 저장, 본인 기록/사진, 스탬프 랭킹·보관소, 데이터랩 논리 ID'),
('favorites.py','회원별 즐겨찾기 추가·해제·조회, 데이터랩 장소 조회 보강'),
('food_rankings.py / food_locations.py','순위 조회와 기존 맛집의 유일한 이름·지역 일치 좌표 연결'),
],[160,340])

page('2-3. 프론트엔드 파일별 역할')
table(['파일','연결 대상 및 역할'],[
('static/js/map.js','/api/regions, /api/landmarks. 행정구역 선택·검색·태그 배치·분류 필터·팝업. CityVisits / CityFavorites / TripTray 호출.'),
('static/js/visits.js','/api/visits, 사진 API. 사진·리뷰 다이얼로그, 방문 체크. visits-updated / stamp-earned / stamps-error 이벤트.'),
('static/js/stamps.js','/api/stamps/ranking. 지도·사이드바 랭킹 동시 갱신. 방문 이벤트로 개인 스탬프 표시.'),
('static/js/stamp-catalog.js','/api/stamps/catalog. 보관소 지역별 목록, 획득 스탬프·지역 보상, ? 설명창.'),
('static/js/favorites.js','/api/favorites. 중복 제거와 버튼 상태, favorites-updated 이벤트.'),
('static/js/trip-tray.js','sessionStorage. 찜 추가·해제·표시. /api/favorites로 하나씩 일괄 저장 후 갱신.'),
('static/js/profile.js','/api/visits와 /api/favorites. 프로필 네 카드와 도시 로고, 사진·리뷰·스탬프 표시.'),
('static/js/account.js','/api/signup, login, logout, profile. 폼 처리·CSRF 헤더·MBTI 정규화.'),
('static/js/recommendations.js','/api/recommendations. 추천 목록을 펼치고 찜·즐겨찾기 버튼 연결.'),
('static/js/sidebar.js','패널 열기·닫기·드래그 핸들·Escape. inert와 aria-hidden 제어.'),
('static/js/draggable-panels.js','로그인·랭킹·찜 상자 이동. 입력·링크·버튼은 드래그 제외. 화면 경계와 크기 변경 처리.'),
('static/images/regions + manifest.csv','지역 로고와 이름·부모지역. 서버가 파일 존재 확인 및 대표색 추출.'),
('static/images/stamps/*.svg','white.svg(깃발), silver.svg(메달), gold.svg(왕관). 공통 스탬프 그림.'),
],[167,333])
add('food-rankings.js 및 auth.js 같은 보존 파일이 있어도, 현재 메인 HTML이 직접 불러오지 않는 파일은 실행 화면에서 자동 동작하지 않습니다. region-puzzle.js는 삭제된 구현입니다.')

page('3. 사진·리뷰와 스탬프 계산')
d=Drawing(500,255)
box(d,0,160,145,75,'장소 상세',['사진·리뷰 입력','본인 세션 + CSRF'])
box(d,180,160,145,75,'POST /api/visits',['이미지 형식 / 5MB 검증','장소 ID 검증'])
box(d,355,160,145,75,'member_visits',['사진 BLOB·후기 저장','같은 장소는 UPDATE'])
edge(d,145,195,180,195);edge(d,325,195,355,195)
box(d,30,25,140,75,'흰색 · 장소',['사진·리뷰 기록 1곳 = 1개'])
box(d,180,25,140,75,'은색 · 시군구',['등록 장소 모두 방문'])
box(d,330,25,165,75,'금색 · 광역단위',['소속 등록 장소 모두 방문'])
edge(d,420,160,420,100);edge(d,380,160,250,100);edge(d,355,160,100,100)
figure(d,'그림 4. 스탬프는 조회 시 계산합니다. 스탬프 전용 테이블이나 별도 영구 발급 기록은 없습니다.')
sub('집계와 ID 규칙')
add('흰색 순위는 회원의 장소별 방문 기록 개수입니다. 은색은 시군구의 대상 장소 ID 집합이 방문 집합에 전부 포함되는지, 금색은 도·특별시·광역시의 대상 집합을 모두 방문했는지 판정합니다. 대상은 기본 장소와 데이터랩 TOP20의 전체 방문자(all) 자료입니다.')
add('동점은 1, 1, 3처럼 공동 순위를 사용합니다. 목록은 최대 5명이며 다른 회원의 이름은 일부 가립니다. 응원 문구는 흰색 패널 하단에서 로그인한 본인 순위에 맞춰 표시합니다.')
add('좌표 없는 데이터랩 맛집 ID = 1,000,000,000,000 + int(poi_id 앞 12자리, 16). 기본 장소 테이블의 ID와 별도 범위를 사용하며 category=food로 기록합니다. 이 연결은 DB 외래키가 아닌 코드 규칙입니다.')
add('표시 태그의 임의 좌표는 브라우저의 _displayPosition입니다. 원래 DB 좌표와 location_url은 바꾸지 않습니다. 좌표가 없는 장소를 실제 매장 위치로 안내하지 않아야 합니다.')

page('4. DB ERD · 지역과 장소')
d=Drawing(500,420)
box(d,180,325,150,80,'regions',['PK code','name / region_type','display_order'])
box(d,15,180,170,95,'localities',['PK id','FK region_code → regions','name / locality_type'])
box(d,315,180,170,95,'geo_admin_codes',['PK source_level + source_code','FK locality_id → localities'])
edge(d,180,350,105,275,'1 : N');edge(d,315,225,185,225,'N : 1')
for x,name in [(0,'tourist_landmarks'),(170,'food_landmarks'),(340,'event_landmarks')]:
    box(d,x,15,160,110,name,['PK id','FK region_code → regions','FK (region_code, locality_id)','→ localities','title / 좌표 / 링크 / 출처'])
    edge(d,100,180,x+80,125,'1 : N')
    if x == 0:
        d.add(Line(180,340,5,340,strokeColor=GRAY));d.add(Line(5,340,5,135,strokeColor=GRAY));edge(d,5,135,40,125,'1 : N')
    elif x == 170:
        edge(d,255,325,255,125,'1 : N')
    else:
        d.add(Line(330,340,498,340,strokeColor=GRAY));d.add(Line(498,340,498,135,strokeColor=GRAY));edge(d,498,135,475,125,'1 : N')
figure(d,'그림 5. 실선은 실제 DB 외래키입니다. 장소 테이블은 regions와 localities에 연결됩니다.')
add('현재 실제 DB에는 관광지·맛집·행사에 locality_id가 존재하고, (region_code, locality_id)로 localities를 참조하는 복합 외래키가 있습니다. 초기 00_schema.sql만 보면 이 관계가 누락되므로 실제 DB 기준 ERD에 반영했습니다.')
table(['실제 관계','설명'],[
('regions.code → localities.region_code','시도 1개에 여러 시군구'),
('localities.id → geo_admin_codes.locality_id','시군구 1개에 SIG/EMD 코드 매핑 여러 개'),
('regions.code → 각 장소.region_code','시도와 장소의 소속'),
('localities.(region_code,id) → 각 장소.(region_code,locality_id)','시군구와 장소의 소속. UI 조회는 아직 region_code + locality_name을 사용.'),
],[265,235])

page('4-2. DB ERD · 회원·기록·데이터랩')
d=Drawing(500,410)
box(d,175,310,160,90,'members',['PK id / UNIQUE username','password_hash / 기본정보','travel_styles / mbti'])
box(d,0,165,210,105,'member_visits',['PK id','UNIQUE member_id+category+landmark_id','review / photo / photo_mime','updated_at'])
box(d,290,165,210,105,'member_favorites',['PK member_id+category+landmark_id','created_at'])
edge(d,215,310,100,270,'1 : N (논리)',True);edge(d,295,310,390,270,'1 : N (논리)',True)
box(d,0,15,220,95,'기본 장소 3종',['tourist / food / event_landmarks','category에 따라 다른 테이블','landmark_id → 해당 id'])
box(d,280,15,220,95,'datalab_food_rankings',['복합 PK: 지역+기간+방문자+POI','v_datalab_food_top20 → area_rank ≤ 20','food 가상 ID → poi_id 규칙'])
edge(d,70,165,90,110,'장소 참조',True);edge(d,165,165,335,110,'가상 ID',True)
edge(d,350,165,165,110,'장소 참조',True);edge(d,440,165,420,110,'가상 ID',True)
figure(d,'그림 6. 점선은 애플리케이션 논리 관계입니다. 회원·방문·즐겨찾기와 데이터랩 간 DB 외래키는 없습니다.')
add('member_visits와 member_favorites는 category + landmark_id로 여러 장소 테이블을 참조합니다. 따라서 단일 장소 테이블 외래키를 선언하지 않았습니다. 삭제되거나 이름이 바뀐 원본 장소를 처리할 때 기록과 집계의 일관성을 따로 확인해야 합니다.')
add('datalab_food_rankings의 기본키는 sigungu_code, period_start, period_end, audience, poi_id입니다. 보관소·정복 집계의 ranking_places()는 all 방문자의 TOP20을 가상 ID로 묶습니다. 지도 화면은 지역별 최신 기간을 선택하므로 집계 대상과 표시 기간의 차이가 생길 수 있습니다.')

page('5. 실제 DB 자료 현황')
table(['테이블 / 뷰','종류','현재 건수'],[(t['name'],t['kind'],f"{t['count']:,}" if t.get('count') is not None else f"조회 오류 {t.get('error_code')}") for t in snapshot['tables']],[265,100,135])
add('기본 지도 장소는 관광지 75 + 맛집 44 + 행사 30 = 149곳입니다. 데이터랩 순위는 25,500행, TOP20 뷰는 5,100행이며, 지역·기간·방문자 구분별 행이므로 전부 서로 다른 식당 수를 뜻하지 않습니다.')
add('회원 2명, 방문 기록 22건, 즐겨찾기 4건은 문서 생성 시점의 스냅샷입니다. 웹을 사용하면 달라질 수 있습니다. 회원별 개인정보나 비밀번호는 스냅샷에 포함하지 않았습니다.')
sub('기존 뷰 오류')
add('v_all_places, v_landmark_counts, v_landmarks는 MariaDB 오류 1356으로 조회되지 않았습니다. 삭제된 원본 참조·컬럼 불일치·권한 문제 중 어느 것인지 이번 문서 작업에서는 확정하지 않았습니다. 현재 앱에서 직접 조회하는 뷰는 v_datalab_food_top20이며 정상 조회했습니다.')

page('6. API와 사용자 흐름')
table(['API','용도 / 접근'],[
('GET /, /signup, /profile','메인·가입·프로필 HTML. 프로필은 로그인 필요.'),
('POST /api/signup, login, logout','CSRF 검증. 비밀번호 해시 저장 / 세션 발급·해제.'),
('POST /api/profile','본인 기본정보 수정. username/password/password_hash 요청은 차단.'),
('GET /api/regions, /api/landmarks','시도 목록과 장소 조회. scope=all 또는 region+locality, category 필터.'),
('GET /api/food-rankings/options, /api/food-rankings','데이터랩 지역·기간·방문자 구분별 순위.'),
('GET/POST /api/visits','본인의 기록 조회와 사진·리뷰 저장. POST는 CSRF 필수.'),
('GET /api/visits/<id>/photo','해당 회원의 사진만 제공, no-store.'),
('GET/POST /api/favorites','본인 목록 조회, 추가·해제. active=true 일괄 저장은 중복 추가 방지.'),
('GET /api/stamps/ranking?type=white|silver|gold','TOP 5, 본인 순위, 각 회원의 3종 수량. 읽기 API.'),
('GET /api/stamps/catalog','본인 획득 여부와 대상 장소. 로그인 필요.'),
('GET /api/recommendations','본인 MBTI로 기존 DB 장소 추천. 로그인 필요.'),
],[240,260])
d=Drawing(500,145)
box(d,0,45,145,80,'임시 찜',['장소 팝업의 ♡','sessionStorage'])
box(d,180,45,145,80,'일괄 추가',['POST /api/favorites 반복','성공/실패 건수 안내'])
box(d,355,45,145,80,'즐겨찾기 목록',['같은 저장소로 통합','중복 없이 5곳 + 더보기'])
edge(d,145,85,180,85);edge(d,325,85,355,85)
figure(d,'그림 7. 찜과 즐겨찾기의 저장 경계. 찜 자체는 영구 DB 저장이 아닙니다.')

page('7. 실행·검증과 현재 제한사항')
sub('실행')
add('프로젝트 루트에서 .venv/Scripts/python.exe app.py를 실행하고 http://127.0.0.1:5000에 접속합니다. .env는 DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, SECRET_KEY를 제공하며 Git에서 제외됩니다. DB 이름은 cityname으로 코드에 고정되어 있습니다.')
add('requirements.txt에는 Flask, PyMySQL, python-dotenv 외에 용도를 확인하지 않은 yangjaedeok 줄이 있습니다. 환경 설치 목록을 정리할 때 검토해야 합니다. PDF 생성에는 별도로 reportlab과 Pillow를 사용했습니다.')
sub('이번 문서 작업의 검증')
add('실제 DB에서 테이블·컬럼·외래키·건수를 읽었습니다. 기존 테스트 전체 21개가 통과했습니다. 파일 관계는 현재 HTML의 script 참조와 Python의 라우트 등록 기준으로 정리했습니다. 브라우저 자동화로 전체 UI·드래그·애니메이션을 검증한 보고서는 아닙니다.')
sub('운영 전 점검할 내용')
add('• 스탬프는 별도 발급 이력 없이 동적 계산됩니다. 대상 장소 추가·삭제에 따라 은색·금색 획득 상태가 달라질 수 있습니다.<br/>• 데이터랩 가상 ID는 POI 앞 12자리 규칙입니다. 충돌 가능성 및 원본 변경 처리는 별도의 검증이 필요합니다.<br/>• 기본 장소와 데이터랩 장소의 동일 실제 업소가 다른 ID로 남으면 집계 대상이 중복될 수 있습니다.<br/>• 추천은 텍스트 키워드이며 실제 소음·인기도·혼잡도 정보가 아닙니다. MBTI는 성향 참고로 사용합니다.<br/>• 지도 태그는 실제 좌표 대신 지역 안에 임의 배치됩니다. 경계 안 배치·긴 이름·작은 지역은 브라우저로 추가 확인해야 합니다.<br/>• 임시 찜은 같은 탭 저장소를 사용합니다. 계정 변경 시 목록 분리 정책은 아직 없습니다.<br/>• 일괄 즐겨찾기는 순차 API 호출이라 일부 성공 후 실패할 수 있으며 성공 수를 안내합니다.<br/>• 사진 검증은 헤더와 크기 기준입니다. 이미지 재인코딩과 실제 방문 위치 인증은 구현되지 않았습니다.<br/>• UI CSS가 누적되어 있습니다. 유지보수 시 중복 규칙과 사용하지 않는 퍼즐 스타일을 정리할 수 있습니다.')
sub('DB 변경으로 실제 추가한 것')
add('members.mbti CHAR(4) NULL 컬럼을 추가했습니다. 이 변경의 재현 SQL은 db/migrations/20261015_member_mbti.sql입니다. 새 스탬프 DB·테이블은 만들지 않았습니다. 기존 회원 데이터는 유지하고 시연용 방문 20건을 저장했습니다.')

page('부록 A. 실제 테이블 컬럼 사전')
for item in snapshot['tables']:
    if item['kind']!='BASE TABLE':continue
    sub(item['name'])
    table(['컬럼','자료형','키','NULL'],[(c['Field'],c['Type'],c['Key'] or '-',c['Null']) for c in item['columns']],[155,205,75,65])

page('부록 B. 실제 외래키와 문서 산출물')
table(['자식 테이블·컬럼','부모 테이블·컬럼'],[(f"{r['TABLE_NAME']}.{r['COLUMN_NAME']}",f"{r['REFERENCED_TABLE_NAME']}.{r['REFERENCED_COLUMN_NAME']}") for r in snapshot['foreign_keys']],[270,230])
add('같은 장소 테이블의 region_code와 locality_id가 localities를 향하는 두 행은 복합 외래키의 구성 컬럼입니다. 상세 제약 이름과 DDL은 서버의 SHOW CREATE TABLE로 추가 확인할 수 있습니다.')
table(['산출물','역할'],[
('docs/generated/travel_drawer_report.pdf','본 문서'),
('docs/generated/schema_snapshot.json','컬럼·건수·외래키만 담은 스키마 스냅샷. 사용자 데이터 원문 없음.'),
('docs/generated/build_project_report.py','맑은 고딕을 포함한 PDF 재생성 스크립트'),
],[285,215])

def footer(canvas,doc):
    canvas.saveState();canvas.setStrokeColor(colors.HexColor('#d3dfcf'));canvas.line(42,35,553,35)
    canvas.setFont('Korean',7);canvas.setFillColor(GRAY);canvas.drawString(42,23,'여행서랍 · 로컬 구현 / DB 구조 · 2026-10-15');canvas.drawRightString(553,23,str(doc.page));canvas.restoreState()
path=OUT/'travel_drawer_report.pdf'
doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=48,title='여행서랍 변경사항·파일 연결관계·DB ERD',author='Travel Drawer Project')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print(str(path))
