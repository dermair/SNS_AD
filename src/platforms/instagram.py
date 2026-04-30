"""인스타그램 포맷터 — 피드/릴스 최적화 출력."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.core.config import OUTPUT_DIR
from src.models.content import InstagramContent


class InstagramFormatter:
    """InstagramContent를 게시 가능한 형식으로 변환."""

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or OUTPUT_DIR / "instagram"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def format_caption(self, content: InstagramContent) -> str:
        """캡션 + 해시태그 전체 텍스트."""
        hashtags_str = " ".join(f"#{tag}" for tag in content.hashtags)

        return f"""{content.caption}

.
.
.
{hashtags_str}"""

    def format_full(self, content: InstagramContent) -> str:
        """전체 콘텐츠 정보 포함 텍스트."""
        sections = [
            f"# 인스타그램 콘텐츠",
            f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 캡션",
            content.caption,
            "",
            "## 해시태그",
            " ".join(f"#{tag}" for tag in content.hashtags),
            f"(총 {len(content.hashtags)}개)",
            "",
            "## 이미지 설명",
            content.image_description or "(없음)",
        ]

        if content.image_path:
            sections.extend(["", f"## 생성된 이미지", content.image_path])

        if content.reels_script:
            sections.extend(["", "## 릴스 스크립트", content.reels_script])

        if content.carousel_texts:
            sections.append("")
            sections.append("## 캐러셀 텍스트")
            for i, text in enumerate(content.carousel_texts, 1):
                sections.append(f"  [{i}] {text}")

        return "\n".join(sections)

    def save(self, content: InstagramContent) -> str:
        """콘텐츠를 파일로 저장하고 경로를 반환."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        text = self.format_full(content)
        filename = f"instagram_{timestamp}.md"
        file_path = self.output_dir / filename
        file_path.write_text(text, encoding="utf-8")

        # 캡션만 별도 저장 (복사-붙여넣기용)
        caption_file = self.output_dir / f"caption_{timestamp}.txt"
        caption_file.write_text(self.format_caption(content), encoding="utf-8")

        return str(file_path)
