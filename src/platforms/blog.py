"""블로그 포맷터 — 네이버 블로그 최적화 출력."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.core.config import OUTPUT_DIR
from src.models.content import BlogContent


class BlogFormatter:
    """BlogContent를 네이버 블로그 게시 가능한 형식으로 변환."""

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or OUTPUT_DIR / "blog"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def format_markdown(self, content: BlogContent) -> str:
        """마크다운 형식으로 포맷팅."""
        tags_str = " ".join(f"#{tag}" for tag in content.tags)
        seo_str = ", ".join(content.seo_keywords)

        return f"""---
title: "{content.title}"
seo_keywords: [{seo_str}]
meta_description: "{content.meta_description}"
tags: [{', '.join(content.tags)}]
created: {datetime.now().strftime('%Y-%m-%d %H:%M')}
thumbnail: {content.thumbnail_path or 'N/A'}
---

# {content.title}

{content.body}

---
{tags_str}
"""

    def format_html(self, content: BlogContent) -> str:
        """네이버 블로그 에디터용 HTML 형식."""
        paragraphs = content.body.split("\n\n")
        html_parts = []

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if para.startswith("## "):
                html_parts.append(f"<h3>{para[3:]}</h3>")
            elif para.startswith("### "):
                html_parts.append(f"<h4>{para[4:]}</h4>")
            else:
                html_parts.append(f"<p>{para}</p>")

        body_html = "\n".join(html_parts)
        tags_html = " ".join(f"<span>#{tag}</span>" for tag in content.tags)

        return f"""<div class="blog-post">
<h2>{content.title}</h2>
{body_html}
<div class="tags">{tags_html}</div>
</div>"""

    def save(self, content: BlogContent, fmt: str = "markdown") -> str:
        """콘텐츠를 파일로 저장하고 경로를 반환."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if fmt == "html":
            text = self.format_html(content)
            ext = "html"
        else:
            text = self.format_markdown(content)
            ext = "md"

        filename = f"blog_{timestamp}.{ext}"
        file_path = self.output_dir / filename
        file_path.write_text(text, encoding="utf-8")
        return str(file_path)
