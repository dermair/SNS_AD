"""블로그 에이전트 — 네이버 블로그 SEO 최적화 포스트 생성."""

from __future__ import annotations

import json

from src.core.config import ShopProfile
from src.core.llm import LLMClient, LLMProvider
from src.core.image_gen import ImageGenerator
from src.core.prompts import BLOG_SYSTEM, BLOG_USER
from src.models.content import BlogContent


class BlogAgent:
    """네이버 블로그 콘텐츠 전문 에이전트."""

    def __init__(
        self,
        llm: LLMClient,
        shop: ShopProfile,
        image_gen: ImageGenerator | None = None,
    ):
        self.llm = llm
        self.shop = shop
        self.image_gen = image_gen

    async def generate(
        self,
        direction: str,
        keywords: list[str],
        provider: LLMProvider = LLMProvider.CLAUDE,
        image_prompt: str | None = None,
        guidelines_override: str = "",
        blog_info: dict | None = None,
    ) -> BlogContent:
        """블로그 포스트를 생성한다."""
        # YAML 기본 지침 + CLI 오버라이드 합성
        guidelines_parts = []
        if self.shop.blog_guidelines.to_prompt_string():
            guidelines_parts.append(self.shop.blog_guidelines.to_prompt_string())
        if guidelines_override:
            guidelines_parts.append(guidelines_override)

        guidelines_text = ""
        if guidelines_parts:
            guidelines_text = "\n\n[블로그 작성 지침]\n" + "\n\n".join(guidelines_parts)

        # input/blog/info.yaml 정보 자동 로드
        if blog_info is None:
            from src.utils.blog_input import load_blog_info
            blog_info = load_blog_info()

        blog_info_text = ""
        if blog_info:
            from src.utils.blog_input import blog_info_to_prompt
            blog_info_text = "\n\n[고객 정보 및 사진 배치]\n" + blog_info_to_prompt(blog_info)
            blog_info_text += "\n\n위 고객 정보와 사진 파일명을 본문에 반드시 반영하세요."
            blog_info_text += "\n사진이 들어갈 위치에 (파일명: before_1.jpg — 케어 전 볼/턱 사진) 형식으로 표기하세요."

        prompt = BLOG_USER.format(
            shop_context=self.shop.to_context_string(),
            direction=direction,
            keywords=", ".join(keywords),
            blog_guidelines=guidelines_text + blog_info_text,
        )

        response = await self.llm.generate(
            prompt=prompt,
            provider=provider,
            system=BLOG_SYSTEM,
            max_tokens=4096,
            temperature=0.7,
        )

        content = self._parse_response(response)

        # 썸네일 이미지 생성
        if image_prompt and self.image_gen:
            try:
                image_result = await self.image_gen.generate(
                    prompt=image_prompt,
                    platform="blog",
                    style="professional beauty blog thumbnail",
                )
                content.thumbnail_path = image_result.get("path")
            except Exception as e:
                print(f"[블로그] 이미지 생성 실패: {e}")

        return content

    def _parse_response(self, response: str) -> BlogContent:
        """LLM 응답을 BlogContent로 파싱."""
        try:
            # ```json 코드블록 제거
            text = response
            if "```" in text:
                text = text.replace("```json", "").replace("```", "")
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
                return BlogContent(
                    title=data.get("title", ""),
                    body=data.get("body", ""),
                    tags=data.get("tags", []),
                    seo_keywords=data.get("seo_keywords", []),
                    meta_description=data.get("meta_description", ""),
                )
        except json.JSONDecodeError:
            pass

        # 파싱 실패 시 원문 그대로 사용
        return BlogContent(title="(제목 생성 실패)", body=response)
