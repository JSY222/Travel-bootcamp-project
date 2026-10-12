from flask import Flask, render_template, jsonify
import pymysql
from pymysql.cursors import DictCursor

app = Flask(__name__)

# MariaDB 연결 설정
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "123",  # 본인의 MariaDB 비밀번호 입력
    "database": "cityname",
    "charset": "utf8mb4",
    "cursorclass": DictCursor
}


def get_conn():
    return pymysql.connect(**DB_CONFIG)


# 메인 웹페이지
@app.get("/")
def index():
    return render_template("index.html")


# 14개 시도 조회
@app.get("/api/regions")
def get_regions():
    conn = None

    try:
        conn = get_conn()

        with conn.cursor() as cursor:
            sql = """
                SELECT id, name, official_name
                FROM regions
                ORDER BY id
            """
            cursor.execute(sql)
            rows = cursor.fetchall()

        return jsonify({
            "ok": True,
            "regions": rows
        })

    except Exception as e:
        app.logger.exception("지역 조회 오류")
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500

    finally:
        if conn:
            conn.close()


# 선택한 지역의 시군구 조회
@app.get("/api/regions/<int:region_id>/divisions")
def get_divisions(region_id):
    conn = None

    try:
        conn = get_conn()

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name
                FROM administrative_divisions
                WHERE region_id = %s
                ORDER BY name
                """,
                (region_id,)
            )
            rows = cursor.fetchall()

        return jsonify({
            "ok": True,
            "divisions": rows
        })

    except Exception as e:
        app.logger.exception("시군구 조회 오류")
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    app.run(debug=True, port=5000)