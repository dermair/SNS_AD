"""SEO 키워드 헬퍼 — 네이버 블로그 및 유튜브 최적화 (피부관리 전문)."""

from __future__ import annotations


# 피부관리 관련 SEO 키워드 풀
SKINCARE_SEO_KEYWORDS: dict[str, list[str]] = {
    "수분관리": [
        "수분관리 추천", "수분관리 가격", "수분케어 효과", "건조피부 관리",
        "강남 수분관리", "피부관리실 수분", "보습 관리 추천",
    ],
    "여드름관리": [
        "여드름관리 추천", "여드름관리 가격", "여드름 피부관리실",
        "트러블 관리 추천", "강남 여드름관리", "성인여드름 관리",
    ],
    "모공관리": [
        "모공관리 추천", "모공관리 가격", "모공축소 관리", "블랙헤드 관리",
        "강남 모공관리", "모공 피부관리실", "피지 모공 관리",
    ],
    "리프팅관리": [
        "리프팅 추천", "리프팅 가격", "탄력 관리 추천", "안티에이징 관리",
        "강남 리프팅", "피부 리프팅 관리", "주름 관리 추천",
    ],
    "톤업관리": [
        "톤업 관리 추천", "미백 관리 가격", "피부톤 관리", "잡티 관리",
        "강남 톤업관리", "브라이트닝 관리", "기미 관리 추천",
    ],
    "재생관리": [
        "재생관리 추천", "필링 관리 가격", "피부재생 관리", "흉터 관리",
        "강남 재생관리", "피부장벽 관리", "민감피부 관리",
    ],
    "LED테라피": [
        "LED 피부관리 추천", "LED테라피 효과", "LED 관리 가격",
        "강남 LED관리", "피부진정 관리",
    ],
}


def get_seo_keywords(
    service: str,
    location: str = "",
    extra: list[str] | None = None,
    max_count: int = 10,
) -> list[str]:
    """시술에 맞는 SEO 키워드 목록을 반환.

    Args:
        service: 시술 종류
        location: 지역명 (예: "강남")
        extra: 추가 키워드
        max_count: 최대 키워드 수
    """
    keywords: list[str] = []

    # 시술별 기본 키워드
    if service in SKINCARE_SEO_KEYWORDS:
        keywords.extend(SKINCARE_SEO_KEYWORDS[service])

    # 지역 조합 키워드
    if location:
        keywords.append(f"{location} {service}")
        keywords.append(f"{location} {service} 추천")
        keywords.append(f"{location} {service} 가격")
        keywords.append(f"{location} 피부관리실")

    if extra:
        keywords.extend(extra)

    # 중복 제거
    seen = set()
    unique = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)

    return unique[:max_count]


def optimize_blog_title(title: str, primary_keyword: str) -> str:
    """블로그 제목에 SEO 키워드를 최적화.

    네이버 C-Rank 알고리즘은 제목 앞쪽의 키워드를 더 중시한다.
    """
    if title.startswith(primary_keyword):
        return title

    # 키워드가 이미 포함되어 있으면 앞으로 이동
    if primary_keyword in title:
        title_without = title.replace(primary_keyword, "").strip()
        clean = title_without.lstrip("| - ,:")
        return f"{primary_keyword} {clean}"

    # 키워드가 없으면 앞에 추가
    return f"{primary_keyword} | {title}"


def generate_meta_description(title: str, body_preview: str, max_length: int = 160) -> str:
    """메타 설명을 생성. 네이버 검색 결과에 표시되는 설명문."""
    desc = f"{title} - {body_preview}"
    if len(desc) > max_length:
        desc = desc[: max_length - 3] + "..."
    return desc
