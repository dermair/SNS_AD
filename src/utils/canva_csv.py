"""Canva 대량제작용 CSV 생성 — 카드뉴스 텍스트를 CSV로 내보내기."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from src.core.config import OUTPUT_DIR


def generate_card_news_csv(
    slides: list[dict],
    output_path: Path | None = None,
) -> str:
    """카드뉴스 슬라이드 데이터를 Canva 대량제작용 CSV로 저장한다.

    Args:
        slides: [{"title": "제목", "body": "본문", "sub": "서브텍스트"}, ...]
        output_path: 저장 경로 (미지정 시 자동 생성)

    Returns:
        저장된 CSV 파일 경로
    """
    if not output_path:
        csv_dir = OUTPUT_DIR / "instagram" / "canva"
        csv_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = csv_dir / f"cardnews_{timestamp}.csv"

    # Canva 대량제작은 첫 행이 헤더, 이후 행이 데이터
    # 각 행 = 1장의 슬라이드
    fieldnames = ["slide", "title", "body", "sub"]

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, slide in enumerate(slides, 1):
            writer.writerow({
                "slide": i,
                "title": slide.get("title", ""),
                "body": slide.get("body", ""),
                "sub": slide.get("sub", ""),
            })

    return str(output_path)
