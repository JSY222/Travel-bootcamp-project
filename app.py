"""Cityname travel map — run: python app.py"""
import os
from flask import Flask, jsonify, render_template, request
import pymysql
from dotenv import load_dotenv
# test
load_dotenv()
from pymysql.cursors import DictCursor

app = Flask(__name__)

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

    if not (len(region) == 2 and region.isdigit()) or not (1 <= len(locality) <= 50):
        return jsonify({'ok': False, 'error': '올바른 지역과 시·군·구를 선택하세요.'}), 400
    if category not in {'all', *TABLES}:
        return jsonify({'ok': False, 'error': '올바르지 않은 카테고리입니다.'}), 400

    chosen = [category] if category != 'all' else list(TABLES)
    results = []
    try:
        # 테이블 이름은 검증된 코드 상수만 삽입, 사용자가 전달한 값은 바인딩
        for kind in chosen:
            rows = fetch_all(
                f'SELECT id, title, description, latitude, longitude, location_url, source_name '
                f'FROM `{TABLES[kind]}` WHERE region_code=%s AND locality_name=%s '
                'ORDER BY id LIMIT 200',
                (region, locality)
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
