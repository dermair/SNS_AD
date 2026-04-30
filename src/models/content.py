"""콘텐츠 데이터 모델."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Platform(str, Enum):
    BLOG = "blog"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"


@dataclass
class ContentRequest:
    """콘텐츠 생성 요청."""
    topic: str
    platforms: list[Platform] = field(default_factory=lambda: list(Platform))
    keywords: list[str] = field(default_factory=list)
    special_instructions: str = ""
    include_image: bool = True
    include_video: bool = False
    blog_guidelines_override: str = ""  # CLI에서 전달하는 추가 지침


@dataclass
class BlogContent:
    """블로그 콘텐츠."""
    title: str = ""
    body: str = ""
    tags: list[str] = field(default_factory=list)
    seo_keywords: list[str] = field(default_factory=list)
    meta_description: str = ""
    thumbnail_path: str | None = None

    def to_markdown(self) -> str:
        tags_str = ", ".join(self.tags)
        return f"""# {self.title}

> 태그: {tags_str}
> SEO 키워드: {', '.join(self.seo_keywords)}

{self.body}
"""


@dataclass
class InstagramContent:
    """인스타그램 콘텐츠."""
    caption: str = ""
    hashtags: list[str] = field(default_factory=list)
    image_description: str = ""
    image_path: str | None = None
    reels_script: str | None = None
    carousel_texts: list[str] = field(default_factory=list)

    def to_text(self) -> str:
        hashtags_str = " ".join(f"#{tag}" for tag in self.hashtags)
        result = f"""{self.caption}

---
{hashtags_str}
"""
        if self.reels_script:
            result += f"\n---\n[릴스 스크립트]\n{self.reels_script}\n"
        if self.carousel_texts:
            result += "\n---\n[캐러셀 텍스트]\n"
            for i, text in enumerate(self.carousel_texts, 1):
                result += f"  슬라이드 {i}: {text}\n"
        return result


@dataclass
class YouTubeContent:
    """유튜브 콘텐츠."""
    title: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    script: str = ""
    thumbnail_text: str = ""
    thumbnail_path: str | None = None
    video_path: str | None = None
    duration_type: str = "shorts"  # "shorts" or "full"

    def to_text(self) -> str:
        tags_str = ", ".join(self.tags)
        return f"""제목: {self.title}
유형: {self.duration_type}

[설명]
{self.description}

[태그] {tags_str}

[썸네일 텍스트] {self.thumbnail_text}

[스크립트]
{self.script}
"""


@dataclass
class ShortsContent:
    """쇼츠/릴스 영상 콘텐츠."""
    title: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    subtitle_segments: list[dict] = field(default_factory=list)
    narration_text: str = ""
    video_path: str | None = None
    mode: str = "slideshow"  # "slideshow" or "narration"
    source_images: list[str] = field(default_factory=list)


@dataclass
class PlatformContent:
    """플랫폼별 생성 결과."""
    platform: Platform
    blog: BlogContent | None = None
    instagram: InstagramContent | None = None
    youtube: YouTubeContent | None = None


@dataclass
class ContentResult:
    """전체 콘텐츠 생성 결과."""
    request: ContentRequest
    contents: list[PlatformContent] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def get_blog(self) -> BlogContent | None:
        for c in self.contents:
            if c.blog:
                return c.blog
        return None

    def get_instagram(self) -> InstagramContent | None:
        for c in self.contents:
            if c.instagram:
                return c.instagram
        return None

    def get_youtube(self) -> YouTubeContent | None:
        for c in self.contents:
            if c.youtube:
                return c.youtube
        return None
