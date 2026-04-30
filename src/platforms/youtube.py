"""유튜브 포맷터 — 영상 메타데이터 + 스크립트 출력."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.core.config import OUTPUT_DIR
from src.models.content import YouTubeContent


class YouTubeFormatter:
    """YouTubeContent를 게시 가능한 형식으로 변환."""

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or OUTPUT_DIR / "youtube"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def format_metadata(self, content: YouTubeContent) -> str:
        """유튜브 업로드용 메타데이터."""
        tags_str = ", ".join(content.tags)

        return f"""제목: {content.title}
유형: {content.duration_type}

[설명]
{content.description}

[태그]
{tags_str}

[썸네일 ��스트]
{content.thumbnail_text}"""

    def format_full(self, content: YouTubeContent) -> str:
        """전체 콘텐츠 정보 포함 텍스트."""
        sections = [
            "# 유튜브 콘텐츠",
            f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"유형: {'쇼츠 (60초)' if content.duration_type == 'shorts' else '일반 영상'}",
            "",
            f"## 제목",
            content.title,
            "",
            "## 설명",
            content.description,
            "",
            "## 태그",
            ", ".join(content.tags),
            "",
            "## 썸네일 텍스트",
            content.thumbnail_text or "(없음)",
        ]

        if content.thumbnail_path:
            sections.extend(["", "## 생성된 썸네일", content.thumbnail_path])

        sections.extend([
            "",
            "## 스크립트",
            "---",
            content.script,
            "---",
        ])

        if content.video_path:
            sections.extend(["", "## 생성된 영상", content.video_path])

        return "\n".join(sections)

    def save(self, content: YouTubeContent) -> str:
        """콘텐츠를 파일로 저장하고 경로를 반환."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        text = self.format_full(content)
        filename = f"youtube_{timestamp}.md"
        file_path = self.output_dir / filename
        file_path.write_text(text, encoding="utf-8")

        # 스크립트만 별도 저장
        script_file = self.output_dir / f"script_{timestamp}.txt"
        script_file.write_text(content.script, encoding="utf-8")

        return str(file_path)
