"""Apply the generated ranking SQL to the configured local cityname database."""
import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv


def main():
    root = Path(__file__).resolve().parent.parent
    load_dotenv(root / '.env')
    path = root / 'db/generated/datalab_food_rankings.sql'
    # Generated data uses hex literals; SQL comments are removed before splitting.
    sql = '\n'.join(line for line in path.read_text(encoding='utf-8').splitlines()
                    if not line.lstrip().startswith('--'))
    conn = pymysql.connect(host=os.getenv('DB_HOST', '127.0.0.1'),
        port=int(os.getenv('DB_PORT', '3306')), user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', '123'), database='cityname',
        charset='utf8mb4', connect_timeout=5)
    try:
        with conn.cursor() as cur:
            for statement in sql.split(';'):
                if statement.strip():
                    cur.execute(statement)
            cur.execute('SELECT COUNT(*),COUNT(DISTINCT sigungu_code) FROM datalab_food_rankings')
            rows, localities = cur.fetchone()
            cur.execute('SELECT COUNT(*) FROM v_datalab_food_top20')
            top20 = cur.fetchone()[0]
        print(f'Applied: {rows} ranking rows, {localities} localities, {top20} TOP20 rows')
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
