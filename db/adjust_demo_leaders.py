"""Add review fixtures to establish requested leaders and one five-way tie."""
import sys
from pathlib import Path
from datetime import timedelta
from collections import Counter
import random

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pymysql
from app import DB_CONFIG, TABLES
from rewards import total_points, award_stamp_points, korea_today
from visits import ranking_places
from db.seed_random_travel_reviews import coins
from db.seed_demo_members import tiny_png


def main():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id,username,name FROM members ORDER BY id')
            members = cur.fetchall()
            highest = max(total_points(cur, m['id'], TABLES) for m in members)
            base = ((highest + 99) // 100) * 100 + 1000
            targets = {'김재환': base+3000, '권민석': base+2000, '양재덕': base+1000}
            cur.execute(' UNION ALL '.join(f"SELECT '{kind}' AS category,id,title,locality_name,region_code FROM `{table}`" for kind, table in TABLES.items()))
            places = cur.fetchall() + ranking_places(cur)
            rng = random.Random(20261016)
            for member in members:
                target = targets.get(member['name'])
                if member['username'] in [f'demo_traveler{i:02d}' for i in range(1,6)]:
                    target = base
                if target is None:
                    continue
                current = total_points(cur, member['id'], TABLES)
                cur.execute('SELECT category,landmark_id FROM member_visits WHERE member_id=%s', (member['id'],))
                owned = {(v['category'],v['landmark_id']) for v in cur.fetchall()}
                reserved, cities = set(), set()
                for place in places:
                    key = (place['category'],place['id'])
                    city = (place['region_code'],place['locality_name'])
                    if city not in cities and key not in owned:
                        cities.add(city)
                        reserved.add(key)
                pool = [p for p in places if (p['category'],p['id']) not in owned | reserved]
                rng.shuffle(pool)
                for age in coins(target-current):
                    p = pool.pop()
                    cur.execute('INSERT INTO member_visits (member_id,category,landmark_id,title,locality_name,review,photo,photo_mime,visited_on) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                                (member['id'],p['category'],p['id'],p['title'],p['locality_name'],f'[여행 테스트] {p["title"]} 방문 기념 사진과 리뷰입니다.',tiny_png(),'image/png',korea_today()-timedelta(days=age)))
                award_stamp_points(cur,member['id'],TABLES)
                if total_points(cur,member['id'],TABLES)!=target:
                    raise RuntimeError('Unexpected reward completion; transaction cancelled')
            results = [(m['name'],total_points(cur,m['id'],TABLES)) for m in members]
            results.sort(key=lambda r:-r[1])
            assert [r[0] for r in results[:3]] == ['김재환','권민석','양재덕']
            assert sorted(n for n in Counter(r[1] for r in results).values() if n>1)==[5]
        conn.commit()
        print('Verified first/second/third:',[r[1] for r in results[:3]])
        print('Five demo users tied at:',base)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
