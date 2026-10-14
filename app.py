"""Cityname travel map — run: python app.py"""
import os
import json
import re
import secrets
from datetime import date
from flask import Flask, jsonify, render_template, request, session
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
    return {'csrf_token': session['csrf_token'], 'member_name': session.get('member_name')}

MEMBERS_SQL = """CREATE TABLE IF NOT EXISTS members (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(50) NOT NULL,
    birth_date DATE NOT NULL,
    address VARCHAR(255) NOT NULL,
    travel_styles JSON NOT NULL,
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
    try:
        birthday = date.fromisoformat(str(data.get('birth_date', '')))
    except ValueError:
        return jsonify(ok=False, error='생년월일을 확인해 주세요.'), 400
    if not (1 <= len(name) <= 50 and re.fullmatch(r'[A-Za-z0-9_]{4,50}', username)
            and isinstance(password, str) and 8 <= len(password) <= 128
            and password == data.get('password_confirmation')
            and 1 <= len(address) <= 255 and birthday <= date.today()
            and isinstance(styles, list) and 1 <= len(styles) <= len(TRAVEL_STYLES)
            and all(isinstance(style, str) and style in TRAVEL_STYLES for style in styles)):
        return jsonify(ok=False, error='입력 내용을 확인하고 여행 스타일을 하나 이상 선택해 주세요.'), 400
    try:
        conn = member_connection()
        try:
            with conn.cursor() as cur:
                cur.execute('INSERT INTO members (username,password_hash,name,birth_date,address,travel_styles) VALUES (%s,%s,%s,%s,%s,%s)',
                            (username, generate_password_hash(password), name, birthday, address, json.dumps(list(dict.fromkeys(styles)), ensure_ascii=False)))
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


def fetch_all(sql, args=()):
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()
    finally:
        conn.close()


@app.get('/')
def index():
    return render_template('index.html')


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
            limit = '' if nationwide else ' LIMIT 200'
            rows = fetch_all(
                f'SELECT id, title, description, latitude, longitude, location_url, source_name '
                f'FROM `{TABLES[kind]}`{where} ORDER BY id{limit}',
                () if nationwide else (region, locality)
            )
            for row in rows:
                row['category'] = kind
                row['latitude'] = float(row['latitude'])
                row['longitude'] = float(row['longitude'])
                results.append(row)
        return jsonify({'ok': True, 'landmarks': results})
    except pymysql.MySQLError:
        app.logger.exception('landmarks query failed')
        return jsonify({'ok': False, 'error': '랜드마크를 조회할 수 없습니다.'}), 500


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
