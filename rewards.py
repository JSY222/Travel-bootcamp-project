"""Permanent, once-per-stamp point awards."""
import json
from datetime import datetime, timedelta, timezone


def korea_today():
    return datetime.now(timezone(timedelta(hours=9))).date()


def remaining_points(original, visited_on, today):
    """Keep full value through day 14; deduct 10% of original per day."""
    minimum = {100: 10, 500: 500, 10000: 1000}.get(original, original // 10)
    decay_days = min(9, max(0, (today - visited_on).days - 14))
    return max(minimum, original * (100 - decay_days * 10) // 100)

REWARDS_SQL = """CREATE TABLE IF NOT EXISTS member_stamp_rewards (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    member_id BIGINT UNSIGNED NOT NULL,
    stamp_type VARCHAR(10) NOT NULL,
    stamp_key VARCHAR(255) NOT NULL,
    points INT UNSIGNED NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_member_stamp (member_id, stamp_type, stamp_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""


def award_stamp_points(cur, member_id, tables, awarded_stamps=None):
    from visits import ranking_places
    # Serialize awards for the same member; visits and awards commit together.
    cur.execute('SELECT id FROM members WHERE id=%s FOR UPDATE', (member_id,))
    if not cur.fetchone():
        raise ValueError('Member not found')
    cur.execute('SELECT category,landmark_id FROM member_visits WHERE member_id=%s', (member_id,))
    owned = {(v['category'], int(v['landmark_id'])) for v in cur.fetchall()}
    cur.execute(' UNION ALL '.join(
        f"SELECT '{kind}' AS category,id,region_code,locality_name FROM `{table}`"
        for kind, table in tables.items()))
    places = cur.fetchall() + ranking_places(cur)
    cities, provinces = {}, {}
    for place in places:
        key = (place['category'], int(place['id']))
        cities.setdefault((place['region_code'], place['locality_name']), set()).add(key)
        provinces.setdefault(place['region_code'], set()).add(key)
    earned = [('white', json.dumps(key, ensure_ascii=False), 100) for key in sorted(owned)]
    for stamp_type, groups, points in [('silver', cities, 500), ('gold', provinces, 10000)]:
        earned.extend((stamp_type, json.dumps(key, ensure_ascii=False), points)
                      for key, required in groups.items() if required and required.issubset(owned))
    awarded = 0
    for stamp_type, key, points in earned:
        cur.execute('INSERT INTO member_stamp_rewards (member_id,stamp_type,stamp_key,points) '
                    'VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE id=id',
                    (member_id, stamp_type, key, points))
        if cur.rowcount == 1:
            awarded += points
            if awarded_stamps is not None:
                awarded_stamps.append(dict(type=stamp_type, points=points))
    return awarded


def total_points(cur, member_id, tables=None):
    if tables is None:
        tables = {'tourism': 'tourist_landmarks', 'food': 'food_landmarks', 'event': 'event_landmarks'}
    return sum(reward['current_points'] for reward in point_history(cur, member_id, tables))


def point_history(cur, member_id, tables, today=None):
    from visits import ranking_places
    cur.execute('SELECT stamp_type,stamp_key,points,created_at FROM member_stamp_rewards '
                'WHERE member_id=%s ORDER BY created_at DESC,id DESC', (member_id,))
    rewards = cur.fetchall()
    cur.execute('SELECT category,landmark_id,title,locality_name,visited_on FROM member_visits '
                'WHERE member_id=%s ORDER BY id DESC', (member_id,))
    visits = cur.fetchall()
    cur.execute(' UNION ALL '.join(
        f"SELECT '{kind}' AS category,id,title,region_code,locality_name FROM `{table}`"
        for kind, table in tables.items()))
    places = {(row['category'], int(row['id'])): row for row in cur.fetchall() + ranking_places(cur)}
    cur.execute('SELECT code,name FROM regions')
    regions = {str(row['code']): row['name'] for row in cur.fetchall()}
    by_place, by_city, by_province = {}, {}, {}
    for visit in visits:
        place_key = (visit['category'], int(visit['landmark_id']))
        place = places.get(place_key, {})
        by_place.setdefault(place_key, []).append(visit)
        by_city.setdefault((place.get('region_code'), place.get('locality_name')), []).append(visit)
        by_province.setdefault(place.get('region_code'), []).append(visit)
    today = today or korea_today()
    for reward in rewards:
        key = json.loads(reward['stamp_key'])
        if reward['stamp_type'] == 'white':
            matched = by_place.get(tuple(key), [])
            place = places.get(tuple(key), {})
            reward['region_code'] = place.get('region_code')
            reward['locality_name'] = place.get('locality_name')
        elif reward['stamp_type'] == 'silver':
            matched = by_city.get(tuple(key), [])
            reward['region_code'], reward['locality_name'] = key
        else:
            matched = by_province.get(key, [])
            reward['region_code'], reward['locality_name'] = key, None
        dates = [v['visited_on'] for v in matched if v['visited_on']]
        reward['last_visited_on'] = max(dates) if dates else None
        # Legacy records have no known visit date; use the original award date
        # without inventing a visit date or modifying the review/history.
        basis = reward['last_visited_on'] or reward['created_at'].date()
        reward['basis_on'] = basis
        reward['decay_starts_on'] = basis + timedelta(days=15)
        reward['current_points'] = remaining_points(int(reward['points']), basis, today)
        reward['deducted_points'] = int(reward['points']) - reward['current_points']
        elapsed = max(0, (today - basis).days)
        reward['remaining_percent'] = reward['current_points'] * 100 // int(reward['points'])
        reward['decay_days'] = min(9, max(0, elapsed - 14))
        reward['minimum_points'] = {'white': 10, 'silver': 500, 'gold': 1000}[reward['stamp_type']]
        reward['daily_deduction'] = int(reward['points']) // 10
        reward['days_until_decay'] = max(0, 15 - elapsed)
        reward['minimum_on'] = basis + timedelta(days=23)
        reward['status'] = 'minimum' if reward['current_points'] <= reward['minimum_points'] else 'full' if elapsed <= 14 else 'decaying'
        reward['next_points'] = remaining_points(int(reward['points']), basis, today + timedelta(days=1))
        if reward['stamp_type'] == 'white':
            reward['title'] = matched[0]['title'] if matched else '이전 방문 장소'
        elif reward['stamp_type'] == 'silver':
            reward['title'] = f'{regions.get(str(key[0]), str(key[0]))} {key[1]}'
        else:
            reward['title'] = regions.get(str(key), str(key))
        reward['place_titles'] = list(dict.fromkeys(v['title'] for v in matched))
    return rewards
