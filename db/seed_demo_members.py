"""Create 20 demo members, each with one review and a tiny valid PNG."""
import json
from pathlib import Path
import struct
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from app import DB_CONFIG, MEMBERS_SQL, TRAVEL_STYLES, app
from visits import VISITS_SQL


def tiny_png():
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\x00\x78\xb4\x96', 9)) + chunk(b'IEND', b''))


def main():
    photo = tiny_png()
    accounts = []
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(MEMBERS_SQL)
            cur.execute(VISITS_SQL)
            cur.execute('SELECT id,title,locality_name FROM tourist_landmarks ORDER BY id LIMIT 20')
            places = cur.fetchall()
            if not places:
                raise RuntimeError('관광지 데이터가 없어 리뷰를 생성할 수 없습니다.')
            for i in range(1, 21):
                username, password = f'demo_traveler{i:02d}', f'TravelDemo{i:02d}!'
                cur.execute('SELECT id FROM members WHERE username=%s', (username,))
                if cur.fetchone():
                    raise RuntimeError(f'{username} 계정이 이미 있습니다. 기존 계정을 변경하지 않고 중단합니다.')
                name = f'더미여행자{i:02d}'
                mbti = ['INFP', 'ENFP', 'ISTJ', 'ESTJ', 'ISFP'][i % 5]
                cur.execute('INSERT INTO members (username,password_hash,name,birth_date,address,travel_styles,mbti) '
                            'VALUES (%s,%s,%s,%s,%s,%s,%s)',
                            (username, generate_password_hash(password), name, f'{1990+i:04d}-01-15',
                             '서울특별시 (더미 데이터)', json.dumps([TRAVEL_STYLES[(i-1) % len(TRAVEL_STYLES)]], ensure_ascii=False), mbti))
                member_id = cur.lastrowid
                place = places[(i-1) % len(places)]
                review = f'[더미 리뷰 {i:02d}] {place["title"]} 방문 기록입니다. 화면과 사진 표시를 확인하기 위한 테스트 데이터입니다.'
                cur.execute('INSERT INTO member_visits (member_id,category,landmark_id,title,locality_name,review,photo,photo_mime) '
                            'VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                            (member_id, 'tourism', place['id'], place['title'], place['locality_name'], review, photo, 'image/png'))
                accounts.append((username, password, name))
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    # Exercise real login, review listing, and photo delivery for all accounts.
    with app.test_client() as client:
        for username, password, name in accounts:
            with client.session_transaction() as session:
                session.clear()
                session['csrf_token'] = 'demo-validation'
            response = client.post('/api/login', json=dict(username=username, password=password),
                                   headers={'X-CSRF-Token': 'demo-validation'})
            if response.status_code != 200 or not response.json.get('ok'):
                raise RuntimeError(f'{username}: 로그인 검증 실패')
            response = client.get('/api/visits')
            if response.status_code != 200:
                raise RuntimeError(f'{username}: 리뷰 조회 실패')
    print(f'Created and verified {len(accounts)} accounts; photo: {len(photo)} bytes each.')
    for username, password, name in accounts:
        print(f'{username} | {password} | {name}')


if __name__ == '__main__':
    main()
