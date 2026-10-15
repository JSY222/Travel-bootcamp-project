"""Resolve ranking locations from unambiguous existing restaurant records."""
import math
import unicodedata


def normalized_title(value):
    return ''.join(unicodedata.normalize('NFKC', value).split()).casefold()


def attach_food_locations(rows, region, fetch_all):
    if not rows:
        return rows
    candidates = fetch_all(
        'SELECT id,title,locality_name,latitude,longitude,location_url FROM food_landmarks '
        'WHERE region_code=%s AND latitude IS NOT NULL AND longitude IS NOT NULL', (region,))
    index = {}
    for place in candidates:
        key = (place['locality_name'], normalized_title(place['title']))
        index.setdefault(key, []).append(place)
    for row in rows:
        row.update(latitude=None, longitude=None, landmark_id=None)
        if row.get('poi_id'):
            row['landmark_id'] = 1000000000000 + int(row['poi_id'][:12], 16)
            row['datalab_place'] = True
        matches = index.get((row['locality_name'], normalized_title(row['title'])), [])
        if len(matches) != 1:
            continue
        match = matches[0]
        latitude, longitude = float(match['latitude']), float(match['longitude'])
        if not (math.isfinite(latitude) and math.isfinite(longitude) and 32 <= latitude <= 40 and 124 <= longitude <= 132):
            continue
        row.update(latitude=latitude, longitude=longitude, landmark_id=match['id'],
                   datalab_place=False,
                   location_url=match['location_url'], coordinate_source='food_landmarks')
    return rows
