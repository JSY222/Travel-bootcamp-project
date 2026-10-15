"""Read-only DataLab ranking endpoints; no coordinates are invented."""
import re

import pymysql
from flask import jsonify, request
from food_locations import attach_food_locations


def register_food_ranking_routes(app, fetch_all):
    @app.get('/api/food-rankings/options')
    def food_ranking_options():
        try:
            rows = fetch_all('SELECT DISTINCT region_code,sigungu_code,province_name,locality_name,period_start,period_end '
                             'FROM datalab_food_rankings ORDER BY region_code,sigungu_code,period_end DESC')
            return jsonify(ok=True, options=rows)
        except pymysql.MySQLError:
            app.logger.exception('food ranking options failed')
            return jsonify(ok=False, error='맛집 순위 자료를 불러올 수 없습니다. DB 연결과 순위 SQL 실행 여부를 확인해 주세요.'), 503

    @app.get('/api/food-rankings')
    def food_rankings():
        sigungu = request.args.get('sigungu', '')
        audience = request.args.get('audience', 'all')
        start = request.args.get('start', '')
        end = request.args.get('end', '')
        if (not re.fullmatch(r'[0-9]{5}', sigungu) or audience not in {'all', 'local', 'nonlocal'}
                or any(not re.fullmatch(r'[0-9]{4}(0[1-9]|1[0-2])', period) for period in (start, end))
                or start > end):
            return jsonify(ok=False, error='지역, 기간, 방문자 구분을 확인해 주세요.'), 400
        try:
            rows = fetch_all('SELECT area_rank,title,subtype,poi_id,region_code,sigungu_code,locality_name FROM v_datalab_food_top20 '
                             'WHERE sigungu_code=%s AND audience=%s AND period_start=%s AND period_end=%s '
                             'ORDER BY area_rank,poi_id', (sigungu, audience, start, end))
            if rows:
                attach_food_locations(rows, rows[0]['region_code'], fetch_all)
            mapped = sum(row.get('latitude') is not None for row in rows)
            return jsonify(ok=True, rankings=rows, mapped_count=mapped, missing_coordinates=len(rows) - mapped)
        except pymysql.MySQLError:
            app.logger.exception('food rankings failed')
            return jsonify(ok=False, error='맛집 순위를 조회하지 못했습니다. 잠시 후 다시 시도해 주세요.'), 503
