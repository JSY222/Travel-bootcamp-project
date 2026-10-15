"""Create reward ledger and award points for existing stamps, safely rerunnable."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pymysql
from app import DB_CONFIG, TABLES
from rewards import REWARDS_SQL, award_stamp_points


def main():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(REWARDS_SQL)
            cur.execute('SELECT id FROM members ORDER BY id')
            members = cur.fetchall()
            awarded = sum(award_stamp_points(cur, row['id'], TABLES) for row in members)
        conn.commit()
        print(f'Processed {len(members)} members; newly awarded {awarded} points.')
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
