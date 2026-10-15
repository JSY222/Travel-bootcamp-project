"""Explainable text-keyword ranking, not a psychological prediction."""
STYLE_WORDS = {
    '힐링/자연': ['숲', '산책', '정원', '수목원', '호수', '자연', '휴양', '공원', '해변', '힐링'],
    '액티비티/모험': ['액티비티', '등산', '트레킹', '서핑', '레저', '짚라인', '래프팅', '자전거', '모험', '스포츠'],
    '역사/문화': ['박물관', '미술관', '역사', '문화', '유적', '문화재', '서원', '사찰', '전통', '한옥'],
    '감성/도시': ['카페', '야경', '골목', '거리', '도시', '전망', '사진', '감성', '벽화', '갤러리'],
    '축제/체험형': ['축제', '체험', '페스티벌', '공연', '행사', '공방', '만들기', '놀이', '테마'],
}
MBTI_WORDS = {
    'I': ('차분한 분위기', ['숲', '산책', '정원', '사찰', '호수', '휴양', '조용', '힐링']),
    'E': ('활동과 교류', ['축제', '시장', '공연', '체험', '테마', '거리', '행사']),
    'S': ('직접 보고 체험', ['체험', '전통', '음식', '전시', '유적', '시장', '박물관']),
    'N': ('발견과 영감', ['예술', '미술', '갤러리', '벽화', '전망', '문화', '테마']),
    'T': ('지식과 탐구', ['역사', '과학', '박물관', '유적', '해설', '전시', '문화재']),
    'F': ('감성과 추억', ['감성', '사진', '야경', '정원', '공연', '카페', '힐링']),
    'J': ('목적 있는 관람', ['박물관', '미술관', '전시', '유적', '서원', '문화재', '관람']),
    'P': ('자유로운 탐방', ['산책', '거리', '골목', '시장', '카페', '해변', '자연']),
}


def rank_places(places, mbti, styles, limit=15):
    ranked, seen = [], set()
    for original in places:
        key = (original['category'], original['id'])
        if key in seen:
            continue
        seen.add(key)
        place = dict(original)
        text = f"{place.get('title') or ''} {place.get('description') or ''}"
        matches = {style: [word for word in STYLE_WORDS[style] if word in text]
                   for style in styles if style in STYLE_WORDS}
        matches = {style: words for style, words in matches.items() if words}
        style_score = min(3, len({word for words in matches.values() for word in words})) * 20
        axes = []
        mbti_score = 0
        for letter in mbti:
            label, words = MBTI_WORDS[letter]
            hits = [word for word in words if word in text]
            if hits:
                mbti_score += min(2, len(hits)) * 5
                axes.append(f'{letter} {label}: {", ".join(hits[:2])}')
        place.update(score=style_score+mbti_score, style_score=style_score, mbti_score=mbti_score,
                     match_level='스타일·MBTI 일치' if style_score and mbti_score else '스타일 일치' if style_score else 'MBTI 키워드 일치' if mbti_score else '탐색 추천')
        reasons = [f'{style}: {", ".join(words[:3])}' for style, words in matches.items()] + axes
        place['reason'] = ' / '.join(reasons) if reasons else '일치하는 키워드가 부족해 새로운 여행지 탐색용으로 제안합니다.'
        ranked.append(place)
    ranked.sort(key=lambda p: (-p['score'], -p['style_score'], p['category'], p['id']))
    return ranked[:limit]
