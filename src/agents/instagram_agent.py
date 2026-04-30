"""인스타그램 에이전트 — 피드/릴스 콘텐츠 생성."""

from __future__ import annotations

import json

from src.core.config import ShopProfile
from src.core.llm import LLMClient, LLMProvider
from src.core.image_gen import ImageGenerator
from src.core.prompts import INSTAGRAM_SYSTEM, INSTAGRAM_USER
from src.models.content import InstagramContent


class InstagramAgent:
    """인스타그램 콘텐츠 전문 에이전트."""

    def __init__(self, llm: LLMClient, image_gen: ImageGenerator, shop: ShopProfile):
        self.llm = llm
        self.image_gen = image_gen
        self.shop = shop

    async def generate(
        self,
        direction: str,
        keywords: list[str],
        generate_image: bool = True,
    ) -> InstagramContent:
        """인스타그램 콘텐츠를 생성한다. GPT를 기본 사용."""
        prompt = INSTAGRAM_USER.format(
            shop_context=self.shop.to_context_string(),
            direction=direction,
            keywords=", ".join(keywords),
        )

        response = await self.llm.generate(
            prompt=prompt,
            provider=LLMProvider.CLAUDE,
            system=INSTAGRAM_SYSTEM,
            max_tokens=2048,
            temperature=0.8,
        )

        content = self._parse_response(response)

        # 피드 이미지 생성
        if generate_image and content.image_description:
            try:
                image_result = await self.image_gen.generate_instagram_feed(
                    content.image_description
                )
                content.image_path = image_result.get("path")
            except Exception as e:
                print(f"[인스타그램] 이미지 생성 실패: {e}")

        return content

    def _parse_response(self, response: str) -> InstagramContent:
        """LLM 응답을 InstagramContent로 파싱."""
        try:
            text = response
            if "```" in text:
                text = text.replace("```json", "").replace("```", "")
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
                return InstagramContent(
                    caption=data.get("caption", ""),
                    hashtags=data.get("hashtags", []),
                    image_description=data.get("image_description", ""),
                    reels_script=data.get("reels_script"),
                    carousel_texts=data.get("carousel_texts", []),
                )
        except json.JSONDecodeError:
            pass

        return InstagramContent(caption=response)
