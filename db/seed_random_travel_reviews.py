"""Add randomized review fixtures while preserving all existing records."""
import sys
import random
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pymysql
from app import DB_CONFIG, TABLES
from rewards import award_stamp_points, total_points, korea_today
from visits import ranking_places
from db.seed_demo_members import tiny_png


def coins(amount):
    paths = {0: []}
    for n in range(1, amount + 1):
        for value, age in [(100, 0), (13, 59), (10, 60)]:
            if n - value in paths:
                paths[n] = paths[n-value] + [age]
                break
    if amount not in paths:
        raise RuntimeError('Cannot reach target balance')
    return paths[amount]


def main():
    rng = random.Random(20261015)
    today = korea_today()
    conn = pymysql.connect(**DB_CONFIG)
    report = []
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id,username,name FROM members ORDER BY id')
            members = [m for m in cur.fetchall() if m['name'] in ['김재환', '권민석', '양재덕'] or m['username'].startswith('demo_traveler')]
            if len(members) != 23:
                raise RuntimeError(f'Expected 23 members, found {len(members)}')
            cur.execute(' UNION ALL '.join(f"SELECT '{kind}' AS category,id,title,locality_name,region_code FROM `{table}`" for kind, table in TABLES.items()))
            places = cur.fetchall() + ranking_places(cur)
            photo = tiny_png()
            counts = {}

            def add(member, place, age):
                day = today - timedelta(days=age)
                recorded = datetime.combine(day, datetime.min.time()) + timedelta(hours=rng.randrange(24), minutes=rng.randrange(60))
                review = f'[여행 테스트] {place["title"]}에 방문했습니다. ' + rng.choice(['산책하며 즐거운 시간을 보냈어요.', '다음에도 다시 방문하고 싶어요.', '주변 풍경을 구경하며 쉬어 갔어요.', '여행 추억을 사진으로 남겼어요.'])
                cur.execute('INSERT INTO member_visits (member_id,category,landmark_id,title,locality_name,review,photo,photo_mime,visited_on,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                            (member['id'], place['category'], place['id'], place['title'], place['locality_name'], review, photo, 'image/png', day, recorded))
                counts[member['id']] = counts.get(member['id'], 0) + 1

            pools = {}
            for member in members:
                cur.execute('SELECT category,landmark_id FROM member_visits WHERE member_id=%s', (member['id'],))
                owned = {(r['category'], r['landmark_id']) for r in cur.fetchall()}
                # Reserve one unvisited place in each city so test additions do
                # not accidentally complete a city and introduce extra awards.
                reserved = set()
                seen_cities = set()
                for p in places:
                    city = (p['region_code'], p['locality_name'])
                    key = (p['category'], p['id'])
                    if city not in seen_cities and key not in owned:
                        reserved.add(key)
                        seen_cities.add(city)
                pool = [p for p in places if (p['category'], p['id']) not in owned | reserved]
                rng.shuffle(pool)
                pools[member['id']] = pool
                for _ in range(rng.randint(3, 12)):
                    add(member, pool.pop(), rng.randrange(91))
                award_stamp_points(cur, member['id'], TABLES)
            balances = [total_points(cur, m['id'], TABLES) for m in members]
            base = ((max(balances) + 99) // 100) * 100 + 1000
            for i, member in enumerate(members):
                target = base if i < 5 else base + (i-4)*100
                for age in coins(target - balances[i]):
                    add(member, pools[member['id']].pop(), age)
                award_stamp_points(cur, member['id'], TABLES)
                actual = total_points(cur, member['id'], TABLES)
                if actual != target:
                    raise RuntimeError(f'Balance mismatch: {member["username"]}, {actual} != {target}')
                report.append(dict(username=member['username'], name=member['name'], points=actual, added=counts[member['id']]))
            duplicates = sorted(n for n in Counter(r['points'] for r in report).values() if n>1)
            if duplicates != [5]:
                raise RuntimeError(f'Unexpected tie groups: {duplicates}')
        conn.commit()
        for row in sorted(report, key=lambda r: -r['points']):
            print(f'{row["username"]}: {row["points"]}P, added {row["added"]} photo reviews')
        print('Verified: 23 members, exactly one five-member tie, all other point balances unique.')
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
