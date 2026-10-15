"""Preserve existing reviews while allowing dated repeat visits. Run once."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pymysql
from app import DB_CONFIG
from visits import VISITS_SQL


def main():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(VISITS_SQL)
            cur.execute('SHOW COLUMNS FROM member_visits')
            columns = {row['Field'] for row in cur.fetchall()}
            cur.execute('SHOW INDEX FROM member_visits')
            indexes = {row['Key_name'] for row in cur.fetchall()}
            changes = []
            if 'visited_on' not in columns:
                changes.append('ADD COLUMN visited_on DATE NULL AFTER photo_mime')
            if 'unique_member_place' in indexes:
                changes.append('DROP INDEX unique_member_place')
            if 'member_place' not in indexes:
                changes.append('ADD INDEX member_place (member_id,category,landmark_id)')
            if changes:
                cur.execute('ALTER TABLE member_visits ' + ', '.join(changes))
            conn.commit()
            print('Visit history schema ready; existing dates remain NULL (unknown).')
    finally:
        conn.close()


if __name__ == '__main__':
    main()
