"""설정 관리 모듈 — 환경변수와 샵 프로필 로딩."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
OUTPUT_DIR = PROJECT_ROOT / "output"


@dataclass
class APIKeys:
    anthropic: str = ""
    openai: str = ""
    google: str = ""
    kling_key: str = ""
    kling_secret: str = ""
    instagram_token: str = ""
    instagram_user_id: str = ""
    naver_client_id: str = ""
    naver_client_secret: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    @classmethod
    def from_env(cls) -> APIKeys:
        return cls(
            anthropic=os.getenv("ANTHROPIC_API_KEY", ""),
            openai=os.getenv("OPENAI_API_KEY", ""),
            google=os.getenv("GOOGLE_API_KEY", ""),
            kling_key=os.getenv("KLING_API_KEY", ""),
            kling_secret=os.getenv("KLING_API_SECRET", ""),
            instagram_token=os.getenv("INSTAGRAM_ACCESS_TOKEN", ""),
            instagram_user_id=os.getenv("INSTAGRAM_USER_ID", ""),
            naver_client_id=os.getenv("NAVER_CLIENT_ID", ""),
            naver_client_secret=os.getenv("NAVER_CLIENT_SECRET", ""),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        )

    def validate(self) -> list[str]:
        """누락된 API 키 목록을 반환."""
        missing = []
        if not self.anthropic:
            missing.append("ANTHROPIC_API_KEY")
        if not self.openai:
            missing.append("OPENAI_API_KEY")
        if not self.google:
            missing.append("GOOGLE_API_KEY")
        if not self.kling_key:
            missing.append("KLING_API_KEY")
        return missing


@dataclass
class ServiceInfo:
    name: str
    price_range: str = ""
    duration: str = ""
    keywords: list[str] = field(default_factory=list)


@dataclass
class ToneConfig:
    style: str = "친근하면서도 전문적인"
    target_audience: str = "20-40대 여성"
    key_values: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)


@dataclass
class Promotion:
    title: str
    services: list[str] = field(default_factory=list)
    period: str = ""
    description: str = ""


@dataclass
class BlogGuidelines:
    writing_style: str = ""
    must_include: list[str] = field(default_factory=list)
    must_avoid: list[str] = field(default_factory=list)
    post_structure: list[str] = field(default_factory=list)
    target_length: str = "2000-3000자"
    seo_rules: list[str] = field(default_factory=list)

    def to_prompt_string(self) -> str:
        """프롬프트에 삽입할 블로그 지침 문자열."""
        parts = []
        if self.writing_style:
            parts.append(f"문체: {self.writing_style}")
        if self.must_include:
            items = "\n".join(f"  - {item}" for item in self.must_include)
            parts.append(f"필수 포함:\n{items}")
        if self.must_avoid:
            items = "\n".join(f"  - {item}" for item in self.must_avoid)
            parts.append(f"금지 사항:\n{items}")
        if self.post_structure:
            items = "\n".join(f"  {i}. {item}" for i, item in enumerate(self.post_structure, 1))
            parts.append(f"글 구조:\n{items}")
        if self.target_length:
            parts.append(f"목표 분량: {self.target_length}")
        if self.seo_rules:
            items = "\n".join(f"  - {item}" for item in self.seo_rules)
            parts.append(f"SEO 규칙:\n{items}")
        return "\n".join(parts)


@dataclass
class ShopProfile:
    name: str = ""
    description: str = ""
    location: str = ""
    phone: str = ""
    instagram: str = ""
    blog: str = ""
    youtube: str = ""
    hours: dict[str, str] = field(default_factory=dict)
    services: list[ServiceInfo] = field(default_factory=list)
    tone: ToneConfig = field(default_factory=ToneConfig)
    promotions: list[Promotion] = field(default_factory=list)
    blog_guidelines: BlogGuidelines = field(default_factory=BlogGuidelines)

    @classmethod
    def from_yaml(cls, path: Path | None = None) -> ShopProfile:
        path = path or CONFIG_DIR / "shop_profile.yaml"
        if not path.exists():
            raise FileNotFoundError(f"샵 프로필 파일을 찾을 수 없습니다: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        shop = data.get("shop", {})

        services = [
            ServiceInfo(
                name=s["name"],
                price_range=s.get("price_range", ""),
                duration=s.get("duration", ""),
                keywords=s.get("keywords", []),
            )
            for s in shop.get("services", [])
        ]

        tone_data = shop.get("tone", {})
        tone = ToneConfig(
            style=tone_data.get("style", ""),
            target_audience=tone_data.get("target_audience", ""),
            key_values=tone_data.get("key_values", []),
            avoid=tone_data.get("avoid", []),
        )

        promotions = [
            Promotion(
                title=p["title"],
                services=p.get("services", []),
                period=p.get("period", ""),
                description=p.get("description", ""),
            )
            for p in shop.get("promotions", [])
        ]

        bg_data = shop.get("blog_guidelines", {})
        blog_guidelines = BlogGuidelines(
            writing_style=bg_data.get("writing_style", ""),
            must_include=bg_data.get("must_include", []),
            must_avoid=bg_data.get("must_avoid", []),
            post_structure=bg_data.get("post_structure", []),
            target_length=bg_data.get("target_length", "2000-3000자"),
            seo_rules=bg_data.get("seo_rules", []),
        )

        return cls(
            name=shop.get("name", ""),
            description=shop.get("description", ""),
            location=shop.get("location", ""),
            phone=shop.get("phone", ""),
            instagram=shop.get("instagram", ""),
            blog=shop.get("blog", ""),
            youtube=shop.get("youtube", ""),
            hours=shop.get("hours", {}),
            services=services,
            tone=tone,
            promotions=promotions,
            blog_guidelines=blog_guidelines,
        )

    def to_context_string(self) -> str:
        """에이전트 프롬프트에 삽입할 샵 정보 문자열."""
        services_str = "\n".join(
            f"  - {s.name} ({s.price_range}, {s.duration})" for s in self.services
        )
        promos_str = "\n".join(
            f"  - {p.title}: {p.description} ({p.period})" for p in self.promotions
        )
        values_str = ", ".join(self.tone.key_values)
        avoid_str = ", ".join(self.tone.avoid)

        return f"""[샵 정보]
이름: {self.name}
소개: {self.description}
위치: {self.location}
전화: {self.phone}
인스타그램: {self.instagram}
블로그: {self.blog}
유튜브: {self.youtube}

[시술 메뉴]
{services_str}

[현재 프로모션]
{promos_str}

[톤앤매너]
스타일: {self.tone.style}
타겟: {self.tone.target_audience}
핵심 가치: {values_str}
금지 사항: {avoid_str}"""
