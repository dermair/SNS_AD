"""유튜브 에이전트 — 쇼츠/영상 콘텐츠 생성."""

from __future__ import annotations

import json

from src.core.config import ShopProfile
from src.core.llm import LLMClient, LLMProvider
from src.core.video_gen import VideoGenerator
from src.core.prompts import YOUTUBE_SYSTEM, YOUTUBE_USER
from src.models.content import YouTubeContent


class YouTubeAgent:
    """유튜브 콘텐츠 전문 에이전트."""

    def __init__(self, llm: LLMClient, video_gen: VideoGenerator, shop: ShopProfile):
        self.llm = llm
        self.video_gen = video_gen
        self.shop = shop

    async def generate(
        self,
        direction: str,
        keywords: list[str],
        generate_video: bool = False,
    ) -> YouTubeContent:
        """유튜브 콘텐츠를 생성한다. Claude를 기본 사용."""
        prompt = YOUTUBE_USER.format(
            shop_context=self.shop.to_context_string(),
            direction=direction,
            keywords=", ".join(keywords),
        )

        response = await self.llm.generate(
            prompt=prompt,
            provider=LLMProvider.CLAUDE,
            system=YOUTUBE_SYSTEM,
            max_tokens=4096,
            temperature=0.7,
        )

        content = self._parse_response(response)

        # 영상 생성 (옵션)
        if generate_video and content.script:
            try:
                # 스크립트에서 핵심 장면 설명 추출
                scene_desc = content.script[:200]
                video_result = await self.video_gen.generate_shorts(
                    script=scene_desc,
                    shop_name=self.shop.name,
                )
                # 비동기로 생성 시작 — task_id 저장
                content.video_path = f"[생성중] task_id: {video_result.get('task_id', 'N/A')}"
            except Exception as e:
                print(f"[유튜브] 영상 생성 실패: {e}")

        return content

    def _parse_response(self, response: str) -> YouTubeContent:
        """LLM 응답을 YouTubeContent로 파싱."""
        try:
            text = response
            if "```" in text:
                text = text.replace("```json", "").replace("```", "")
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
                return YouTubeContent(
                    title=data.get("title", ""),
                    description=data.get("description", ""),
                    tags=data.get("tags", []),
                    script=data.get("script", ""),
                    thumbnail_text=data.get("thumbnail_text", ""),
                    duration_type=data.get("duration_type", "shorts"),
                )
        except json.JSONDecodeError:
            pass

        return YouTubeContent(title="(제목 생성 실패)", script=response)
