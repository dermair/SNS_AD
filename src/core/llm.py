"""텍스트 생성 클라이언트 — Claude API + OpenAI GPT 통합 (비동기)."""

from __future__ import annotations

from enum import Enum

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from src.core.config import APIKeys


class LLMProvider(str, Enum):
    CLAUDE = "claude"
    GPT = "gpt"


class LLMClient:
    """Claude API와 OpenAI GPT를 통합하는 비동기 텍스트 생성 클라이언트."""

    def __init__(self, api_keys: APIKeys):
        self._claude = AsyncAnthropic(api_key=api_keys.anthropic)
        self._openai = AsyncOpenAI(api_key=api_keys.openai)

    async def generate(
        self,
        prompt: str,
        provider: LLMProvider = LLMProvider.CLAUDE,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """텍스트를 생성한다.

        Args:
            prompt: 사용자 프롬프트
            provider: 사용할 LLM (claude / gpt)
            system: 시스템 프롬프트
            max_tokens: 최대 토큰 수
            temperature: 생성 온도
        """
        if provider == LLMProvider.CLAUDE:
            return await self._generate_claude(prompt, system, max_tokens, temperature)
        return await self._generate_gpt(prompt, system, max_tokens, temperature)

    async def _generate_claude(
        self, prompt: str, system: str, max_tokens: int, temperature: float
    ) -> str:
        message = await self._claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or "당신은 피부관리실 홍보 콘텐츠 전문 작가입니다.",
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    async def _generate_gpt(
        self, prompt: str, system: str, max_tokens: int, temperature: float
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self._openai.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
