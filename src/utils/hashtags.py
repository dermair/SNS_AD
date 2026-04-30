"""해시태그 생성 유틸리티 — 피부관리 전문."""

from __future__ import annotations

# 피부관리 관련 기본 해시태그 풀
SKINCARE_HASHTAGS = {
    "대형": [  # 100만+ 게시물
        "피부관리", "스킨케어", "뷰티", "피부", "뷰티스타그램",
        "셀프케어", "피부미인", "데일리스킨케어", "글로우", "피부고민",
    ],
    "중형": [  # 1만-100만 게시물
        "피부관리실", "피부케어", "에스테틱", "페이셜", "피부관리추천",
        "모공관리", "여드름관리", "수분관리", "안티에이징", "피부탄력",
        "리프팅", "톤업", "피부재생", "필링", "피부톤",
    ],
    "소형": [  # 1만 이하 게시물 (타겟팅 효과 높음)
        "강남피부관리", "역삼동피부관리", "강남에스테틱", "강남피부관리실",
        "강남페이셜", "역삼피부관리", "강남수분관리", "강남리프팅",
    ],
}

# 시술별 추가 해시태그
SERVICE_HASHTAGS: dict[str, list[str]] = {
    "수분관리": [
        "수분케어", "보습관리", "건조피부", "수분팩", "수분광채",
        "하이드라", "수분부스팅", "촉촉피부", "수분크림추천",
    ],
    "여드름관리": [
        "여드름케어", "트러블케어", "압출관리", "여드름피부", "트러블피부",
        "여드름흉터", "모공여드름", "피지관리", "진정관리",
    ],
    "모공관리": [
        "모공축소", "모공케어", "블랙헤드", "피지관리", "모공청소",
        "딸기코", "모공타이트닝", "모공보이지마",
    ],
    "리프팅관리": [
        "리프팅케어", "탄력관리", "안티에이징관리", "주름관리", "탄력피부",
        "콜라겐관리", "피부탄력케어", "V라인관리",
    ],
    "톤업관리": [
        "미백관리", "톤업케어", "피부톤업", "잡티관리", "기미관리",
        "색소관리", "맑은피부", "화이트닝", "브라이트닝",
    ],
    "재생관리": [
        "피부재생케어", "필링관리", "흉터관리", "피부장벽", "피부복구",
        "셀프힐링", "재생크림", "민감피부케어",
    ],
    "LED테라피": [
        "LED피부관리", "광선관리", "피부진정", "LED마스크", "홈케어LED",
    ],
}

# 시즌별 해시태그
SEASONAL_HASHTAGS: dict[str, list[str]] = {
    "봄": ["봄피부관리", "봄스킨케어", "환절기피부", "봄철피부", "꽃가루피부"],
    "여름": ["여름피부관리", "자외선차단", "썸머스킨케어", "피지관리", "쿨링케어"],
    "가을": ["가을피부관리", "환절기보습", "가을건조", "보습케어", "가을스킨케어"],
    "겨울": ["겨울피부관리", "겨울보습", "건조피부케어", "윈터스킨케어", "각질관리"],
}


def get_season() -> str:
    """현재 계절을 반환."""
    from datetime import datetime
    month = datetime.now().month
    if month in (3, 4, 5):
        return "봄"
    elif month in (6, 7, 8):
        return "여름"
    elif month in (9, 10, 11):
        return "가을"
    return "겨울"


def generate_hashtags(
    service: str = "",
    location_keywords: list[str] | None = None,
    extra: list[str] | None = None,
    max_count: int = 30,
) -> list[str]:
    """플랫폼에 최적화된 해시태그 목록을 생성한다.

    대형:중형:소형 비율을 약 3:5:2로 혼합하여 도달률을 극대화한다.

    Args:
        service: 시술 종류 (예: "수분관리")
        location_keywords: 지역 키워드 (예: ["강남", "역삼동"])
        extra: 추가 해시태그
        max_count: 최대 해시태그 수 (인스타 최대 30개)
    """
    tags: list[str] = []

    # 대형 해시태그 (약 30%)
    large_count = max(3, int(max_count * 0.3))
    tags.extend(SKINCARE_HASHTAGS["대형"][:large_count])

    # 시술별 중형 해시태그 (약 50%)
    mid_count = max(5, int(max_count * 0.5))
    tags.extend(SKINCARE_HASHTAGS["중형"][:mid_count // 2])
    if service and service in SERVICE_HASHTAGS:
        tags.extend(SERVICE_HASHTAGS[service][:mid_count // 2])

    # 소형 해시태그 (약 20%)
    small_count = max(2, int(max_count * 0.2))
    tags.extend(SKINCARE_HASHTAGS["소형"][:small_count])

    # 시즌 해시태그
    season = get_season()
    tags.extend(SEASONAL_HASHTAGS.get(season, [])[:3])

    # 지역 키워드 기반 해시태그
    if location_keywords:
        for loc in location_keywords:
            tags.append(f"{loc}피부관리")
            tags.append(f"{loc}에스테틱")

    # 추가 해시태그
    if extra:
        tags.extend(extra)

    # 중복 제거 + 최대 개수 제한
    seen = set()
    unique_tags = []
    for tag in tags:
        tag_clean = tag.replace("#", "").strip()
        if tag_clean and tag_clean not in seen:
            seen.add(tag_clean)
            unique_tags.append(tag_clean)

    return unique_tags[:max_count]
