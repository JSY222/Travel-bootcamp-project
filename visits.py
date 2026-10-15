"""Private member visit records, with photos stored transactionally in MariaDB."""
import io
import secrets

import pymysql
from flask import jsonify, request, session, send_file

VISITS_SQL = """CREATE TABLE IF NOT EXISTS member_visits (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    member_id BIGINT UNSIGNED NOT NULL,
    category VARCHAR(10) NOT NULL,
    landmark_id BIGINT UNSIGNED NOT NULL,
    title VARCHAR(255) NOT NULL,
    locality_name VARCHAR(100) NOT NULL,
    review TEXT NOT NULL,
    photo MEDIUMBLOB NOT NULL,
    photo_mime VARCHAR(30) NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_member_place (member_id, category, landmark_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""

# Separate ID range for coordinate-free DataLab places; never invent map coordinates.
RANKING_ID_SQL = '(1000000000000 + CONV(SUBSTRING(poi_id,1,12),16,10))'


def ranking_places(cur):
    try:
        cur.execute(f"SELECT 'food' AS category,{RANKING_ID_SQL} AS id,MAX(title) AS title,"
                    'MAX(region_code) AS region_code,MAX(province_name) AS region_name,MAX(locality_name) AS locality_name '
                    "FROM v_datalab_food_top20 WHERE audience='all' GROUP BY id")
        return cur.fetchall()
    except pymysql.MySQLError as error:
        if error.args[0] == 1146:
            return []
        raise


def photo_mime(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if data.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'image/webp'
    return None


def register_visit_routes(app, db_config, tables):
    def connection():
        conn = pymysql.connect(**db_config)
        try:
            with conn.cursor() as cur:
                cur.execute(VISITS_SQL)
            return conn
        except Exception:
            conn.close()
            raise

    @app.get('/api/stamps/catalog')
    def stamp_catalog():
        if not session.get('member_id'):
            return jsonify(ok=False, error='로그인 후 스탬프 도감을 이용해 주세요.'), 401
        try:
            conn = connection()
            try:
                with conn.cursor() as cur:
                    parts = ' UNION ALL '.join(
                        f"SELECT '{kind}' AS category,id,title,region_code,locality_name FROM `{table}`"
                        for kind, table in tables.items())
                    cur.execute(f'SELECT p.*,r.name AS region_name,v.id AS visit_id FROM ({parts}) p '
                                'LEFT JOIN regions r ON r.code=p.region_code '
                                'LEFT JOIN member_visits v ON v.category=p.category AND v.landmark_id=p.id AND v.member_id=%s '
                                'ORDER BY p.region_code,p.locality_name,p.category,p.id', (session['member_id'],))
                    places = cur.fetchall()
                    places += ranking_places(cur)
                    cur.execute('SELECT id,category,landmark_id FROM member_visits WHERE member_id=%s', (session['member_id'],))
                    visited = {(v['category'], v['landmark_id']): v['id'] for v in cur.fetchall()}
                    for place in places:
                        if 'visit_id' not in place:
                            place['visit_id'] = visited.get((place['category'], place['id']))
            finally:
                conn.close()
            response = jsonify(ok=True, places=places)
            response.headers['Cache-Control'] = 'no-store'
            return response
        except pymysql.MySQLError:
            return jsonify(ok=False, error='스탬프 도감을 불러오지 못했습니다.'), 503

    @app.get('/api/stamps/ranking')
    def stamp_ranking():
        stamp_type = request.args.get('type', 'white')
        if stamp_type not in {'white', 'silver', 'gold'}:
            return jsonify(ok=False, error='올바른 스탬프 종류를 선택해 주세요.'), 400
        try:
            conn = connection()
            try:
                with conn.cursor() as cur:
                    cur.execute('SELECT m.id,m.name,COUNT(v.id) AS stamp_count FROM members m '
                                'LEFT JOIN member_visits v ON v.member_id=m.id '
                                'GROUP BY m.id,m.name ORDER BY stamp_count DESC,m.id')
                    rows = cur.fetchall()
                    parts = ' UNION ALL '.join(
                        f"SELECT '{kind}' AS category,id,region_code,locality_name FROM `{table}`"
                        for kind, table in tables.items())
                    cur.execute(parts)
                    places = cur.fetchall() + ranking_places(cur)
                    cities, provinces = {}, {}
                    for place in places:
                        key = (place['category'], int(place['id']))
                        cities.setdefault((place['region_code'], place['locality_name']), set()).add(key)
                        provinces.setdefault(place['region_code'], set()).add(key)
                    cur.execute('SELECT member_id,category,landmark_id FROM member_visits')
                    visits_by_member = {}
                    for visit in cur.fetchall():
                        visits_by_member.setdefault(visit['member_id'], set()).add((visit['category'], int(visit['landmark_id'])))
                    targets = cities if stamp_type == 'silver' else provinces
                    all_places = set().union(*provinces.values()) if provinces else set()
                    owned_by_me = visits_by_member.get(session.get('member_id'), set())
                    progress = {
                        'white': dict(earned=len(all_places & owned_by_me), total=len(all_places)),
                        'silver': dict(earned=sum(required.issubset(owned_by_me) for required in cities.values()), total=len(cities)),
                        'gold': dict(earned=sum(required.issubset(owned_by_me) for required in provinces.values()), total=len(provinces)),
                    } if session.get('member_id') else None
                    for row in rows:
                        owned = visits_by_member.get(row['id'], set())
                        row['stamps'] = {
                            'white': dict(earned=len(owned),total=len(all_places)),
                            'silver': dict(earned=sum(required.issubset(owned) for required in cities.values()),total=len(cities)),
                            'gold': dict(earned=sum(required.issubset(owned) for required in provinces.values()),total=len(provinces)),
                        }
                        if stamp_type != 'white':
                            row['stamp_count'] = sum(bool(required) and required.issubset(owned) for required in targets.values())
                    rows.sort(key=lambda row: (-row['stamp_count'], row['id']))
            finally:
                conn.close()
            ranking = []
            my_rank = None
            previous_count = None
            rank = 0
            for position, row in enumerate(rows, 1):
                count = int(row['stamp_count'])
                if count != previous_count:
                    rank = position
                previous_count = count
                is_me = row['id'] == session.get('member_id')
                entry = dict(rank=rank, name='나' if is_me else (row['name'][:1] + '○○'),
                             stamp_count=count, is_me=is_me, stamps=row['stamps'])
                if is_me:
                    my_rank = entry
                if len(ranking) < 5:
                    ranking.append(entry)
            response = jsonify(ok=True, ranking=ranking, my_rank=my_rank, stamp_type=stamp_type, progress=progress)
            response.headers['Cache-Control'] = 'no-store'
            return response
        except pymysql.MySQLError:
            app.logger.exception('stamp ranking failed')
            return jsonify(ok=False, error='스탬프 순위를 불러오지 못했습니다.'), 503

    @app.get('/api/visits')
    def list_visits():
        if not session.get('member_id'):
            return jsonify(ok=False, error='로그인이 필요합니다.'), 401
        try:
            conn = connection()
            try:
                with conn.cursor() as cur:
                    cur.execute('SELECT id,category,landmark_id,title,locality_name,review,updated_at '
                                'FROM member_visits WHERE member_id=%s ORDER BY updated_at DESC,id DESC',
                                (session['member_id'],))
                    visits = cur.fetchall()
                    totals = {}
                    for kind, table in tables.items():
                        cur.execute(f'SELECT COUNT(*) AS total FROM `{table}`')
                        totals[kind] = cur.fetchone()['total']
                    places_sql = ' UNION ALL '.join(
                        f"SELECT '{kind}' AS category,id,region_code,locality_name FROM `{table}`"
                        for kind, table in tables.items())
                    cur.execute(f'SELECT p.*,r.name AS region_name FROM ({places_sql}) p '
                                'LEFT JOIN regions r ON r.code=p.region_code')
                    places = cur.fetchall()
                    places += ranking_places(cur)
            finally:
                conn.close()
            place_index = {(p['category'], p['id']): p for p in places}
            regional_totals = {}
            for place in places:
                key = (place['region_code'], place['locality_name'])
                if key not in regional_totals:
                    regional_totals[key] = dict(region_code=key[0], locality_name=key[1],
                                               region_name=place['region_name'], total=0)
                regional_totals[key]['total'] += 1
            for visit in visits:
                place = place_index.get((visit['category'], visit['landmark_id']))
                visit['region_code'] = place['region_code'] if place else None
                visit['region_name'] = place['region_name'] if place else None
                if place:
                    visit['locality_name'] = place['locality_name']
                visit['photo_url'] = f"/api/visits/{visit['id']}/photo"
                visit['updated_at'] = visit['updated_at'].isoformat()
            response = jsonify(ok=True, visits=visits, totals=totals,
                               regional_totals=list(regional_totals.values()))
            response.headers['Cache-Control'] = 'no-store'
            return response
        except pymysql.MySQLError:
            app.logger.exception('visit list failed')
            return jsonify(ok=False, error='방문 기록을 불러올 수 없습니다. DB 연결을 확인해 주세요.'), 503

    @app.post('/api/visits')
    def save_visit():
        if not session.get('member_id'):
            return jsonify(ok=False, error='로그인 후 방문 기록을 남겨 주세요.'), 401
        token = request.headers.get('X-CSRF-Token', '')
        if not token or not secrets.compare_digest(token, session.get('csrf_token', '')):
            return jsonify(ok=False, error='페이지를 새로고침해 주세요.'), 400
        category = request.form.get('category', '')
        landmark_id = request.form.get('landmark_id', '')
        review = request.form.get('review', '').strip()
        if category not in tables or not landmark_id.isascii() or not landmark_id.isdigit() or not 1 <= len(review) <= 2000:
            return jsonify(ok=False, error='장소와 리뷰(1~2000자)를 확인해 주세요.'), 400
        if len(landmark_id) > 18:
            return jsonify(ok=False, error='올바르지 않은 장소입니다.'), 400
        upload = request.files.get('photo')
        photo = upload.read(5 * 1024 * 1024 + 1) if upload and upload.filename else None
        mime = photo_mime(photo) if photo else None
        if photo is not None and (not mime or len(photo) > 5 * 1024 * 1024):
            return jsonify(ok=False, error='사진은 5MB 이하의 JPG, PNG, WebP 파일을 선택해 주세요.'), 400
        try:
            conn = connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(f'SELECT title,locality_name FROM `{tables[category]}` WHERE id=%s', (int(landmark_id),))
                    place = cur.fetchone()
                    if not place and category == 'food' and int(landmark_id) >= 1000000000000:
                        cur.execute(f'SELECT title,locality_name FROM datalab_food_rankings WHERE {RANKING_ID_SQL}=%s LIMIT 1', (int(landmark_id),))
                        place = cur.fetchone()
                    if not place:
                        return jsonify(ok=False, error='존재하지 않는 장소입니다.'), 404
                    if photo is None:
                        cur.execute('SELECT photo,photo_mime FROM member_visits WHERE member_id=%s AND category=%s AND landmark_id=%s',
                                    (session['member_id'], category, int(landmark_id)))
                        old = cur.fetchone()
                        if not old:
                            return jsonify(ok=False, error='방문 사진을 선택해 주세요.'), 400
                        photo, mime = old['photo'], old['photo_mime']
                    cur.execute('INSERT INTO member_visits (member_id,category,landmark_id,title,locality_name,review,photo,photo_mime) '
                                'VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE '
                                'title=VALUES(title),locality_name=VALUES(locality_name),review=VALUES(review),photo=VALUES(photo),photo_mime=VALUES(photo_mime)',
                                (session['member_id'], category, int(landmark_id), place['title'], place['locality_name'], review, photo, mime))
                conn.commit()
            finally:
                conn.close()
            return jsonify(ok=True)
        except pymysql.MySQLError:
            app.logger.exception('visit save failed')
            return jsonify(ok=False, error='저장하지 못했습니다. DB 연결을 확인해 주세요.'), 503

    @app.get('/api/visits/<int:visit_id>/photo')
    def visit_photo(visit_id):
        if not session.get('member_id'):
            return jsonify(ok=False, error='로그인이 필요합니다.'), 401
        try:
            conn = connection()
            try:
                with conn.cursor() as cur:
                    cur.execute('SELECT photo,photo_mime FROM member_visits WHERE id=%s AND member_id=%s',
                                (visit_id, session['member_id']))
                    visit = cur.fetchone()
            finally:
                conn.close()
            if not visit:
                return jsonify(ok=False, error='사진을 찾을 수 없습니다.'), 404
            response = send_file(io.BytesIO(visit['photo']), mimetype=visit['photo_mime'])
            response.headers['Cache-Control'] = 'no-store'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            return response
        except pymysql.MySQLError:
            app.logger.exception('visit photo failed')
            return jsonify(ok=False, error='사진을 불러올 수 없습니다.'), 503
