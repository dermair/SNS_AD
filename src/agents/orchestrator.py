"""오케스트레이터 에이전트 — 콘텐츠 생성 총괄 코디네이터."""

from __future__ import annotations

import asyncio
import json

from src.core.config import APIKeys, ShopProfile
from src.core.llm import LLMClient, LLMProvider
from src.core.image_gen import ImageGenerator
from src.core.video_gen import VideoGenerator
from src.core.prompts import ORCHESTRATOR_SYSTEM, ORCHESTRATOR_USER
from src.models.content import (
    ContentRequest,
    ContentResult,
    Platform,
    PlatformContent,
)
from src.agents.blog_agent import BlogAgent
from src.agents.instagram_agent import InstagramAgent
from src.agents.youtube_agent import YouTubeAgent


class Orchestrator:
    """콘텐츠 생성을 총괄하는 메인 에이전트."""

    def __init__(self, shop_profile: ShopProfile, api_keys: APIKeys):
        self.shop = shop_profile
        self.llm = LLMClient(api_keys)
        self.image_gen = ImageGenerator(api_keys)
        self.video_gen = VideoGenerator(api_keys)

        self.blog_agent = BlogAgent(self.llm, self.shop, self.image_gen)
        self.instagram_agent = InstagramAgent(self.llm, self.image_gen, self.shop)
        self.youtube_agent = YouTubeAgent(self.llm, self.video_gen, self.shop)

    async def generate(self, request: ContentRequest) -> ContentResult:
        """콘텐츠를 생성한다.

        1. 주제를 분석하여 플랫폼별 전략을 수립
        2. 플랫폼별 에이전트를 병렬 호출
        3. 결과를 통합하여 반환
        """
        # 1단계: 전략 수립 (Claude)
        strategy = await self._analyze_topic(request)

        # 2단계: 플랫폼별 에이전트 병렬 호출
        tasks = []
        for platform in request.platforms:
            if platform == Platform.BLOG:
                tasks.append(self._run_blog(strategy, request))
            elif platform == Platform.INSTAGRAM:
                tasks.append(self._run_instagram(strategy, request))
            elif platform == Platform.YOUTUBE:
                tasks.append(self._run_youtube(strategy, request))

        contents = await asyncio.gather(*tasks, return_exceptions=True)

        # 3단계: 결과 통합
        result = ContentResult(request=request)
        for content in contents:
            if isinstance(content, PlatformContent):
                result.contents.append(content)
            elif isinstance(content, Exception):
                print(f"[오류] 콘텐츠 생성 실패: {content}")

        return result

    async def _analyze_topic(self, request: ContentRequest) -> dict:
        """주제를 분석하여 플랫폼별 전략을 수립한다."""
        prompt = ORCHESTRATOR_USER.format(
            shop_context=self.shop.to_context_string(),
            topic=request.topic,
            special_instructions=(
                f"추가 지시: {request.special_instructions}"
                if request.special_instructions
                else ""
            ),
        )

        response = await self.llm.generate(
            prompt=prompt,
            provider=LLMProvider.CLAUDE,
            system=ORCHESTRATOR_SYSTEM,
            temperature=0.5,
        )

        try:
            # JSON 부분만 추출
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

        # 파싱 실패 시 기본 전략
        return {
            "topic_analysis": request.topic,
            "keywords": request.keywords or [request.topic],
            "blog_direction": f"{request.topic}에 대한 정보형 블로그 포스트",
            "instagram_direction": f"{request.topic} 소개 피드 포스트",
            "youtube_direction": f"{request.topic} 소개 쇼츠",
            "image_prompts": [f"skincare clinic {request.topic}"],
            "video_prompt": f"skincare clinic {request.topic} showcase",
        }

    async def _run_blog(self, strategy: dict, request: ContentRequest) -> PlatformContent:
        keywords = strategy.get("keywords", [request.topic])
        direction = strategy.get("blog_direction", "")
        blog_content = await self.blog_agent.generate(
            direction=direction,
            keywords=keywords,
            image_prompt=strategy.get("image_prompts", [""])[0] if request.include_image else None,
            guidelines_override=request.blog_guidelines_override,
        )
        return PlatformContent(platform=Platform.BLOG, blog=blog_content)

    async def _run_instagram(self, strategy: dict, request: ContentRequest) -> PlatformContent:
        keywords = strategy.get("keywords", [request.topic])
        direction = strategy.get("instagram_direction", "")
        insta_content = await self.instagram_agent.generate(
            direction=direction,
            keywords=keywords,
            generate_image=request.include_image,
        )
        return PlatformContent(platform=Platform.INSTAGRAM, instagram=insta_content)

    async def _run_youtube(self, strategy: dict, request: ContentRequest) -> PlatformContent:
        keywords = strategy.get("keywords", [request.topic])
        direction = strategy.get("youtube_direction", "")
        yt_content = await self.youtube_agent.generate(
            direction=direction,
            keywords=keywords,
            generate_video=request.include_video,
        )
        return PlatformContent(platform=Platform.YOUTUBE, youtube=yt_content)
