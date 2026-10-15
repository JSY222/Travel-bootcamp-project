"""Cityname travel map — run: python app.py"""
import os
import json
import re
import secrets
import csv
from pathlib import Path
from datetime import date
from flask import Flask, jsonify, render_template, request, session, redirect, url_for, make_response
import pymysql
from dotenv import load_dotenv

load_dotenv()
from pymysql.cursors import DictCursor

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY') or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')
from werkzeug.security import generate_password_hash, check_password_hash

TRAVEL_STYLES = ['힐링/자연', '액티비티/모험', '역사/문화', '감성/도시', '축제/체험형']

@app.context_processor
def auth_context():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    points = 0
    if session.get('member_id'):
        try:
            from rewards import total_points
            conn = pymysql.connect(**DB_CONFIG)
            try:
                with conn.cursor() as cur:
                    points = total_points(cur, session['member_id'], TABLES)
            finally:
                conn.close()
        except pymysql.MySQLError:
            app.logger.exception('member points query failed')
    return {'csrf_token': session['csrf_token'], 'member_name': session.get('member_name'), 'member_points': points}

MEMBERS_SQL = """CREATE TABLE IF NOT EXISTS members (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(50) NOT NULL,
    birth_date DATE NOT NULL,
    address VARCHAR(255) NOT NULL,
    travel_styles JSON NOT NULL,
    mbti CHAR(4) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""


def member_connection():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(MEMBERS_SQL)
        return conn
    except Exception:
        conn.close()
        raise


def auth_payload():
    token = request.headers.get('X-CSRF-Token', '')
    if not token or not secrets.compare_digest(token, session.get('csrf_token', '')):
        return None
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


@app.get('/signup')
def signup_page():
    return render_template('signup.html', travel_styles=TRAVEL_STYLES)


@app.post('/api/signup')
def signup():
    data = auth_payload()
    if data is None:
        return jsonify(ok=False, error='페이지를 새로고침한 후 다시 시도해 주세요.'), 400
    name = str(data.get('name', '')).strip()
    username = str(data.get('username', '')).strip()
    password = data.get('password', '')
    address = str(data.get('address', '')).strip()
    styles = data.get('travel_styles', [])
    mbti = str(data.get('mbti', '')).upper()
    try:
        birthday = date.fromisoformat(str(data.get('birth_date', '')))
    except ValueError:
        return jsonify(ok=False, error='생년월일을 확인해 주세요.'), 400
    if not (1 <= len(name) <= 50 and re.fullmatch(r'[A-Za-z0-9_]{4,50}', username)
            and isinstance(password, str) and 8 <= len(password) <= 128
            and password == data.get('password_confirmation')
            and 1 <= len(address) <= 255 and birthday <= date.today()
            and isinstance(styles, list) and 1 <= len(styles) <= len(TRAVEL_STYLES)
            and all(isinstance(style, str) and style in TRAVEL_STYLES for style in styles)
            and re.fullmatch(r'[A-Z]{4}', mbti)):
        return jsonify(ok=False, error='입력 내용을 확인하고 여행 스타일을 하나 이상 선택해 주세요.'), 400
    try:
        conn = member_connection()
        try:
            with conn.cursor() as cur:
                cur.execute('INSERT INTO members (username,password_hash,name,birth_date,address,travel_styles,mbti) VALUES (%s,%s,%s,%s,%s,%s,%s)',
                            (username, generate_password_hash(password), name, birthday, address, json.dumps(list(dict.fromkeys(styles)), ensure_ascii=False), mbti))
            conn.commit()
        finally:
            conn.close()
        return jsonify(ok=True), 201
    except pymysql.IntegrityError:
        return jsonify(ok=False, error='이미 있는 id/pw입니다'), 409
    except pymysql.MySQLError:
        app.logger.exception('member registration failed')
        return jsonify(ok=False, error='회원 정보를 저장할 수 없습니다. DB 연결을 확인해 주세요.'), 503


@app.post('/api/login')
def login():
    data = auth_payload()
    if data is None:
        return jsonify(ok=False, error='페이지를 새로고침한 후 다시 시도해 주세요.'), 400
    username = str(data.get('username', '')).strip()
    password = data.get('password', '')
    if not username or len(username) > 50 or not isinstance(password, str) or not 1 <= len(password) <= 128:
        return jsonify(ok=False, error='아이디와 비밀번호를 확인해 주세요.'), 400
    try:
        conn = member_connection()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT id,name,password_hash FROM members WHERE username=%s', (username,))
                member = cur.fetchone()
        finally:
            conn.close()
        if member is None:
            return jsonify(ok=False, error='등록되지 않은 아이디입니다. 회원가입을 진행해 주세요.', signup_required=True), 404
        if not check_password_hash(member['password_hash'], password):
            return jsonify(ok=False, error='비밀번호가 일치하지 않습니다.'), 401
        session.clear()
        session.update(member_id=member['id'], member_name=member['name'], csrf_token=secrets.token_hex(32))
        return jsonify(ok=True)
    except pymysql.MySQLError:
        app.logger.exception('member login failed')
        return jsonify(ok=False, error='로그인할 수 없습니다. DB 연결을 확인해 주세요.'), 503


@app.post('/api/logout')
def logout():
    if auth_payload() is None:
        return jsonify(ok=False, error='페이지를 새로고침해 주세요.'), 400
    session.clear()
    return jsonify(ok=True)


DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', '123'),
    'database': 'cityname',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor,
    'connect_timeout': 5,
}

# 표 이름을 입력값으로 직접 사용하면 SQL 인젝션이 생기므로 화이트리스트로 제한
TABLES = {'tourism': 'tourist_landmarks', 'food': 'food_landmarks', 'event': 'event_landmarks'}
from visits import register_visit_routes
app.config['MAX_CONTENT_LENGTH'] = 6 * 1024 * 1024
register_visit_routes(app, DB_CONFIG, TABLES)
from favorites import register_favorite_routes
register_favorite_routes(app, DB_CONFIG, TABLES, auth_payload)


@app.errorhandler(413)
def upload_too_large(error):
    return jsonify(ok=False, error='파일이 너무 큽니다. 사진은 5MB 이하로 선택해 주세요.'), 413


def fetch_all(sql, args=()):
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()
    finally:
        conn.close()


from food_rankings import register_food_ranking_routes
register_food_ranking_routes(app, fetch_all)


def load_region_icons():
    icon_root = Path(app.static_folder) / 'images' / 'regions'
    icons = []
    manifest = icon_root / 'manifest.csv'
    if manifest.is_file():
        with manifest.open(encoding='utf-8-sig', newline='') as source:
            for row in csv.DictReader(source):
                if (icon_root / row['path']).is_file():
                    svg = (icon_root / row['path']).read_text(encoding='utf-8')
                    colors = re.findall(r'#[0-9a-fA-F]{6}\b', svg)
                    accent = '#608a86'
                    best_score = 0
                    for color in set(colors):
                        rgb = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
                        saturation = max(rgb) - min(rgb)
                        score = colors.count(color) * saturation
                        if saturation > 45 and 35 < sum(rgb) / 3 < 220 and score > best_score:
                            accent, best_score = color, score
                    icons.append({'name': row['name_ko'], 'parent': row['parent_ko'],
                                  'accent': accent,
                                  'region_code': Path(row['path']).parts[0].split('_', 1)[0],
                                  'level': row['level'],
                                  'url': url_for('static', filename='images/regions/' + row['path'],
                                                 v=(icon_root / row['path']).stat().st_mtime_ns)})
    return icons


@app.get('/')
def index():
    map_version = (Path(app.static_folder) / 'js' / 'map.js').stat().st_mtime_ns
    return render_template('index.html', region_icons=load_region_icons(), map_version=map_version)


@app.get('/profile')
def profile():
    if not session.get('member_id'):
        return redirect(url_for('index'))
    try:
        # Only the authenticated member's record is accessible; never fetch passwords.
        rows = fetch_all(
            'SELECT username,name,birth_date,address,travel_styles,mbti FROM members WHERE id=%s',
            (session['member_id'],)
        )
    except pymysql.MySQLError:
        app.logger.exception('profile query failed')
        response = make_response(render_template('profile.html', member=None,
            error='프로필을 불러올 수 없습니다. 잠시 후 다시 시도해 주세요.'), 503)
    else:
        if not rows:
            session.clear()
            return redirect(url_for('index'))
        member = dict(rows[0])
        styles = member.get('travel_styles')
        if isinstance(styles, (str, bytes)):
            try:
                styles = json.loads(styles)
            except (ValueError, TypeError):
                styles = []
        member['travel_styles'] = [style for style in styles if isinstance(style, str)] if isinstance(styles, list) else []
        response = make_response(render_template('profile.html', member=member, region_icons=load_region_icons(), travel_styles=TRAVEL_STYLES))
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.post('/api/profile')
def update_profile():
    if not session.get('member_id'):
        return jsonify(ok=False, error='로그인이 필요합니다.'), 401
    data = auth_payload()
    if data is None:
        return jsonify(ok=False, error='페이지를 새로고침해 주세요.'), 400
    if 'password_hash' in data:
        return jsonify(ok=False, error='잘못된 요청입니다.'), 400
    username = data.get('username')
    password = data.get('password', '')
    current_password = data.get('current_password', '')
    if username is not None and (not isinstance(username, str) or not re.fullmatch(r'[A-Za-z0-9_]{4,50}', username)):
        return jsonify(ok=False, error='아이디는 영문, 숫자, 밑줄로 4~50자 입력해 주세요.'), 400
    if not isinstance(password, str) or (password and not 8 <= len(password) <= 128):
        return jsonify(ok=False, error='새 비밀번호는 8~128자 입력해 주세요.'), 400
    if password != data.get('password_confirmation', ''):
        return jsonify(ok=False, error='새 비밀번호가 일치하지 않습니다.'), 400
    name = str(data.get('name', '')).strip()
    address = str(data.get('address', '')).strip()
    mbti = str(data.get('mbti', '')).upper()
    styles = data.get('travel_styles', [])
    try:
        birthday = date.fromisoformat(str(data.get('birth_date', '')))
    except ValueError:
        return jsonify(ok=False, error='생년월일을 확인해 주세요.'), 400
    if not (1 <= len(name) <= 50 and 1 <= len(address) <= 255 and birthday <= date.today()
            and re.fullmatch(r'[A-Z]{4}', mbti) and isinstance(styles, list) and 1 <= len(styles) <= len(TRAVEL_STYLES)
            and all(isinstance(style, str) and style in TRAVEL_STYLES for style in styles)):
        return jsonify(ok=False, error='기본정보와 MBTI(영문자 4글자)를 확인해 주세요.'), 400
    try:
        conn = member_connection()
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT id,username,password_hash FROM members WHERE id=%s FOR UPDATE', (session['member_id'],))
                member = cur.fetchone()
                if not member:
                    return jsonify(ok=False, error='회원 정보를 찾을 수 없습니다.'), 404
                username = member['username'] if username is None else username
                if password or username != member['username']:
                    if not isinstance(current_password, str) or not 1 <= len(current_password) <= 128 or not check_password_hash(member['password_hash'], current_password):
                        return jsonify(ok=False, error='현재 비밀번호를 확인해 주세요.'), 400
                if password and check_password_hash(member['password_hash'], password):
                    return jsonify(ok=False, code='same_password', error='기존 비밀번호와 같습니다. 다른 비밀번호를 입력해 주세요.'), 400
                password_hash = generate_password_hash(password) if password else member['password_hash']
                cur.execute('UPDATE members SET username=%s,password_hash=%s,name=%s,birth_date=%s,address=%s,travel_styles=%s,mbti=%s WHERE id=%s',
                            (username, password_hash, name, birthday, address, json.dumps(list(dict.fromkeys(styles)), ensure_ascii=False), mbti, session['member_id']))
            conn.commit()
        finally:
            conn.close()
        session['member_name'] = name
        return jsonify(ok=True)
    except pymysql.IntegrityError:
        return jsonify(ok=False, error='이미 사용 중인 아이디입니다. 다른 아이디를 입력해 주세요.'), 409
    except pymysql.MySQLError:
        return jsonify(ok=False, error='회원 정보를 수정하지 못했습니다.'), 503


@app.get('/points')
def points_page():
    if not session.get('member_id'):
        return redirect(url_for('index'))
    from rewards import point_history
    filters = {key: request.args.get(key, '').strip() for key in ('start', 'end', 'region', 'locality')}
    context = dict(filters=filters, region_options=[], localities={}, page=1, pages=1, result_count=0)
    try:
        conn = pymysql.connect(**DB_CONFIG)
        try:
            with conn.cursor() as cur:
                history = point_history(cur, session['member_id'], TABLES)
                cur.execute('SELECT code,name FROM regions ORDER BY display_order')
                region_options = cur.fetchall()
        finally:
            conn.close()
        localities = {}
        for row in history:
            if row['region_code'] and row['locality_name']:
                localities.setdefault(str(row['region_code']), set()).add(row['locality_name'])
        context.update(region_options=region_options, localities={key: sorted(value) for key, value in localities.items()})
        invalid_date = False
        try:
            start = date.fromisoformat(filters['start']) if filters['start'] else None
            end = date.fromisoformat(filters['end']) if filters['end'] else None
            if start and end and start > end:
                raise ValueError
        except ValueError:
            invalid_date = True
        if invalid_date:
            filtered = []
            context['error'] = '검색 날짜를 확인해 주세요. 시작일은 종료일보다 늦을 수 없습니다.'
        else:
            filtered = [row for row in history
                        if (not start or (row['last_visited_on'] and row['last_visited_on'] >= start))
                        and (not end or (row['last_visited_on'] and row['last_visited_on'] <= end))
                        and (not filters['region'] or str(row['region_code']) == filters['region'])
                        and (not filters['locality'] or row['locality_name'] == filters['locality'])]
        pages = max(1, (len(filtered) + 9) // 10)
        page = min(pages, max(1, request.args.get('page', 1, type=int) or 1))
        context.update(page=page, pages=pages, result_count=len(filtered),
                       member_points=sum(row['current_points'] for row in history))
        response = make_response(render_template('points.html', history=filtered[(page-1)*10:page*10], **context))
    except pymysql.MySQLError:
        app.logger.exception('point history query failed')
        response = make_response(render_template('points.html', history=[], error='포인트 내역을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.', **context), 503)
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.get('/api/recommendations')
def recommendations():
    if not session.get('member_id'):
        return jsonify(ok=False, error='로그인하면 내 MBTI에 맞춘 추천을 볼 수 있어요.'), 401
    try:
        from recommendations import rank_places, STYLE_WORDS
        members = fetch_all('SELECT mbti,travel_styles FROM members WHERE id=%s', (session['member_id'],))
        mbti = (members[0].get('mbti') or '').upper() if members else ''
        if not re.fullmatch(r'[IE][NS][FT][JP]', mbti):
            return jsonify(ok=False, error='내 프로필에 INFP, ESTJ처럼 올바른 MBTI를 입력해 주세요.'), 400
        styles = members[0].get('travel_styles') or []
        if isinstance(styles, (str, bytes)):
            try:
                styles = json.loads(styles)
            except (ValueError, TypeError):
                styles = []
        styles = list(dict.fromkeys(style for style in styles if isinstance(style, str) and style in STYLE_WORDS)) if isinstance(styles, list) else []
        candidates = []
        for category, table in TABLES.items():
            places = fetch_all(f'SELECT l.id,l.title,l.description,l.locality_name,l.region_code,l.location_url,l.latitude,l.longitude,r.name AS region_name '
                               f'FROM `{table}` l LEFT JOIN regions r ON r.code=l.region_code')
            candidates.extend(dict(place, category=category) for place in places)
        results = rank_places(candidates, mbti, styles)
        return jsonify(ok=True, mbti=mbti, travel_styles=styles, places=results)
    except pymysql.MySQLError:
        return jsonify(ok=False, error='추천 장소를 불러오지 못했습니다.'), 503


@app.get('/api/regions')
def get_regions():
    try:
        rows = fetch_all('SELECT code, name, region_type FROM regions ORDER BY display_order')
        return jsonify({'ok': True, 'regions': rows})
    except pymysql.MySQLError:
        app.logger.exception('regions query failed')
        return jsonify({'ok': False, 'error': 'DB 연결 실패. DB 설정과 SQL 초기화를 확인하세요.'}), 500


@app.get('/api/landmarks')
def get_landmarks():
    region = request.args.get('region', '').strip()
    locality = request.args.get('locality', '').strip()
    category = request.args.get('category', 'all').strip()
    nationwide = request.args.get('scope', '') == 'all'

    if (nationwide and (region or locality)) or (not nationwide and (
        not (len(region) == 2 and region.isdigit()) or not (1 <= len(locality) <= 50)
    )):
        return jsonify({'ok': False, 'error': '올바른 지역과 시·군·구를 선택하세요.'}), 400
    if category not in {'all', *TABLES}:
        return jsonify({'ok': False, 'error': '올바르지 않은 카테고리입니다.'}), 400

    chosen = [category] if category != 'all' else list(TABLES)
    results = []
    try:
        # 테이블 이름은 검증된 코드 상수만 삽입, 사용자가 전달한 값은 바인딩
        for kind in chosen:
            where = '' if nationwide else ' WHERE region_code=%s AND locality_name=%s'
            rows = fetch_all(
                f'SELECT id, title, description, latitude, longitude, location_url, source_name, region_code '
                f'FROM `{TABLES[kind]}`{where} ORDER BY id',
                () if nationwide else (region, locality)
            )
            for row in rows:
                row['category'] = kind
                row['latitude'] = float(row['latitude']) if row['latitude'] is not None else None
                row['longitude'] = float(row['longitude']) if row['longitude'] is not None else None
                results.append(row)
        rankings = []
        if not nationwide and category in {'all', 'food'}:
            # Ranking records have no coordinates and must never become fake map pins.
            canonical_region = {'51': '42', '52': '45'}.get(region, region)
            locality_prefix = locality.replace('!', '!!').replace('%', '!%').replace('_', '!_') + ' %'
            try:
                rankings = fetch_all(
                    'SELECT r.area_rank,r.title,r.subtype,r.poi_id,r.locality_name,r.period_start,r.period_end '
                    'FROM v_datalab_food_top20 r WHERE r.region_code=%s AND r.audience=%s '
                    "AND (r.locality_name=%s OR r.locality_name LIKE %s ESCAPE '!') "
                    'AND NOT EXISTS (SELECT 1 FROM datalab_food_rankings n '
                    'WHERE n.sigungu_code=r.sigungu_code AND n.audience=r.audience '
                    'AND (n.period_end>r.period_end OR (n.period_end=r.period_end AND n.period_start>r.period_start))) '
                    'ORDER BY r.locality_name,r.area_rank,r.poi_id',
                    (canonical_region, 'all', locality, locality_prefix))
            except pymysql.MySQLError as error:
                if error.args[0] != 1146:
                    raise
        if rankings:
            from food_locations import attach_food_locations
            attach_food_locations(rankings, canonical_region, fetch_all)
        return jsonify({'ok': True, 'landmarks': results, 'food_rankings': rankings})
    except pymysql.MySQLError:
        app.logger.exception('landmarks query failed')
        return jsonify({'ok': False, 'error': '랜드마크를 조회할 수 없습니다.'}), 500


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
