"""Member-scoped, idempotent landmark favorites."""
import pymysql
from visits import ranking_places, RANKING_ID_SQL
from flask import jsonify, session

FAVORITES_SQL = """CREATE TABLE IF NOT EXISTS member_favorites (
    member_id BIGINT UNSIGNED NOT NULL,
    category VARCHAR(10) NOT NULL,
    landmark_id BIGINT UNSIGNED NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (member_id,category,landmark_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""


def register_favorite_routes(app, db_config, tables, auth_payload):
    def connection():
        conn = pymysql.connect(**db_config)
        try:
            with conn.cursor() as cur:
                cur.execute(FAVORITES_SQL)
            return conn
        except Exception:
            conn.close()
            raise

    @app.get('/api/favorites')
    def list_favorites():
        if not session.get('member_id'):
            return jsonify(ok=False, error='로그인 후 즐겨찾기를 이용해 주세요.'), 401
        try:
            conn = connection()
            try:
                places = []
                with conn.cursor() as cur:
                    for category, table in tables.items():
                        cur.execute('SELECT l.id,l.title,l.description,l.latitude,l.longitude,l.location_url,l.source_name,l.locality_name '
                                    f'FROM member_favorites f JOIN `{table}` l ON l.id=f.landmark_id '
                                    'WHERE f.member_id=%s AND f.category=%s ORDER BY f.created_at DESC,l.id',
                                    (session['member_id'], category))
                        for row in cur.fetchall():
                            row['category'] = category
                            row['latitude'] = float(row['latitude'])
                            row['longitude'] = float(row['longitude'])
                            places.append(row)
                    cur.execute("SELECT landmark_id FROM member_favorites WHERE member_id=%s AND category='food' AND landmark_id>=1000000000000", (session['member_id'],))
                    rank_ids = {row['landmark_id'] for row in cur.fetchall()}
                    if rank_ids:
                        for row in ranking_places(cur):
                            if int(row['id']) in rank_ids:
                                row.update(description='데이터랩 맛집 · 위치 미확인',latitude=None,longitude=None,location_url='',source_name='한국관광 데이터랩',datalab_place=True)
                                places.append(row)
            finally:
                conn.close()
            response = jsonify(ok=True, landmarks=places)
            response.headers['Cache-Control'] = 'no-store'
            return response
        except pymysql.MySQLError:
            app.logger.exception('favorites list failed')
            return jsonify(ok=False, error='즐겨찾기를 불러오지 못했습니다. 다시 시도해 주세요.'), 503

    @app.post('/api/favorites')
    def save_favorite():
        if not session.get('member_id'):
            return jsonify(ok=False, error='로그인 후 즐겨찾기를 이용해 주세요.'), 401
        data = auth_payload()
        if data is None:
            return jsonify(ok=False, error='페이지를 새로고침한 후 다시 시도해 주세요.'), 400
        category = data.get('category')
        place_id = data.get('landmark_id')
        active = data.get('active')
        if not isinstance(category, str) or category not in tables or type(place_id) is not int or not 0 < place_id < 10**18 or type(active) is not bool:
            return jsonify(ok=False, error='올바르지 않은 즐겨찾기 요청입니다.'), 400
        try:
            conn = connection()
            try:
                with conn.cursor() as cur:
                    if active:
                        cur.execute(f'SELECT id FROM `{tables[category]}` WHERE id=%s', (place_id,))
                        found = cur.fetchone()
                        if not found and category == 'food' and place_id >= 1000000000000:
                            cur.execute(f'SELECT poi_id FROM datalab_food_rankings WHERE {RANKING_ID_SQL}=%s LIMIT 1', (place_id,))
                            found = cur.fetchone()
                        if not found:
                            return jsonify(ok=False, error='존재하지 않는 장소입니다.'), 404
                        cur.execute('INSERT INTO member_favorites (member_id,category,landmark_id) VALUES (%s,%s,%s) '
                                    'ON DUPLICATE KEY UPDATE landmark_id=VALUES(landmark_id)',
                                    (session['member_id'], category, place_id))
                    else:
                        cur.execute('DELETE FROM member_favorites WHERE member_id=%s AND category=%s AND landmark_id=%s',
                                    (session['member_id'], category, place_id))
                conn.commit()
            finally:
                conn.close()
            return jsonify(ok=True, active=active)
        except pymysql.MySQLError:
            app.logger.exception('favorite save failed')
            return jsonify(ok=False, error='즐겨찾기를 저장하지 못했습니다. 다시 시도해 주세요.'), 503
