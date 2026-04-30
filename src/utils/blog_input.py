"""블로그 입력 정보 로더 — input/blog/info.yaml 파싱."""

from __future__ import annotations

from pathlib import Path

import yaml

from src.core.config import PROJECT_ROOT

BLOG_INPUT_DIR = PROJECT_ROOT / "input" / "blog"
INFO_PATH = BLOG_INPUT_DIR / "info.yaml"


def load_blog_info(path: Path | None = None) -> dict | None:
    """input/blog/info.yaml을 로드한다. 없으면 None."""
    p = path or INFO_PATH
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def blog_info_to_prompt(info: dict) -> str:
    """info.yaml 데이터를 프롬프트에 삽입할 텍스트로 변환."""
    parts = []

    # 주제 & 유형
    topic = info.get("topic", "")
    post_type = info.get("post_type", "")
    if topic:
        parts.append(f"주제: {topic}")
    if post_type:
        parts.append(f"글 유형: {post_type}")

    # 고객 케이스
    customers = info.get("customers", [])
    for i, c in enumerate(customers, 1):
        lines = [f"\n[{i}번째 고객 정보]"]
        if c.get("name"):
            lines.append(f"고객: {c['name']} ({c.get('age', '')}, {c.get('gender', '')}, {c.get('job', '')})")
        if c.get("concern"):
            lines.append(f"고민: {c['concern']}")
        if c.get("how_found"):
            lines.append(f"방문 경위: {c['how_found']}")
        if c.get("request"):
            lines.append(f"요청사항: {c['request']}")
        if c.get("care_count"):
            lines.append(f"케어 횟수: {c['care_count']}")
        if c.get("result"):
            lines.append(f"결과: {c['result']}")
        if c.get("review_quote"):
            lines.append(f"고객 후기: \"{c['review_quote']}\"")

        # 사진 정보
        photos = c.get("photos", {})
        if photos:
            photo_lines = []
            if photos.get("before"):
                photo_lines.append(f"케어 전 사진: {photos['before']}")
            if photos.get("after"):
                photo_lines.append(f"케어 후 사진: {photos['after']}")
            if photos.get("other_angle"):
                photo_lines.append(f"다른 각도 사진: {photos['other_angle']}")
            if photo_lines:
                lines.append("사진: " + " / ".join(photo_lines))

        if c.get("review_photo"):
            lines.append(f"후기 사진: {c['review_photo']}")

        parts.append("\n".join(lines))

    # 강조 포인트
    highlights = info.get("highlights", [])
    if highlights:
        items = "\n".join(f"  - {h}" for h in highlights)
        parts.append(f"\n[강조 포인트]\n{items}")

    # FAQ
    faq = info.get("faq", [])
    if faq:
        faq_lines = ["\n[자주 묻는 질문]"]
        for qa in faq:
            faq_lines.append(f"  Q. {qa.get('question', '')}")
            faq_lines.append(f"  A. {qa.get('answer', '')}")
        parts.append("\n".join(faq_lines))

    return "\n".join(parts)


def get_blog_photos(info: dict) -> list[dict]:
    """info.yaml에서 사진 경로 목록을 추출한다."""
    photos = []
    for c in info.get("customers", []):
        p = c.get("photos", {})
        for key in ("before", "after", "other_angle"):
            if p.get(key):
                full_path = BLOG_INPUT_DIR / p[key]
                if full_path.exists():
                    photos.append({"type": key, "path": str(full_path), "customer": c.get("name", "")})
        if c.get("review_photo"):
            full_path = BLOG_INPUT_DIR / c["review_photo"]
            if full_path.exists():
                photos.append({"type": "review", "path": str(full_path), "customer": c.get("name", "")})
    return photos
