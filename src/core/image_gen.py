"""이미지 생성 클라이언트 — Google Gemini (비동기)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import types

from src.core.config import APIKeys, OUTPUT_DIR


class ImageGenerator:
    """Gemini를 사용한 이미지 생성기."""

    def __init__(self, api_keys: APIKeys):
        self._client = genai.Client(api_key=api_keys.google)

    async def generate(
        self,
        prompt: str,
        platform: str = "instagram",
        style: str = "professional skincare clinic photo",
        save: bool = True,
    ) -> dict:
        """이미지를 생성한다.

        Args:
            prompt: 이미지 설명 프롬프트
            platform: 플랫폼 (instagram, blog, youtube)
            style: 이미지 스타일
            save: 파일 저장 여부

        Returns:
            {"path": 저장 경로, "prompt_used": 사용된 프롬프트}
        """
        full_prompt = f"{style}, {prompt}, high quality, studio lighting"

        response = self._client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=full_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        result = {"prompt_used": full_prompt, "path": None}

        if not response.candidates:
            return result

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image_data = part.inline_data.data

                if save and image_data:
                    save_dir = OUTPUT_DIR / platform / "images"
                    save_dir.mkdir(parents=True, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    # inline_data는 이미 바이트일 수 있음
                    image_bytes = image_data if isinstance(image_data, bytes) else image_data.encode()
                    file_path = save_dir / f"{platform}_{timestamp}.png"
                    file_path.write_bytes(image_bytes)
                    result["path"] = str(file_path)

                break

        return result

    async def generate_thumbnail(self, title: str, subtitle: str = "") -> dict:
        """유튜브 썸네일 또는 블로그 대표 이미지를 생성."""
        prompt = (
            f"Skincare clinic promotional thumbnail image. "
            f"Main text concept: '{title}'. "
            f"{'Subtitle: ' + subtitle + '. ' if subtitle else ''}"
            f"Clean, modern design, soft tones, Korean skincare aesthetic"
        )
        return await self.generate(prompt, platform="youtube", style="promotional thumbnail")

    async def generate_instagram_feed(self, description: str) -> dict:
        """인스타그램 피드용 정사각형 이미지를 생성."""
        prompt = (
            f"Instagram feed photo, square format 1:1 ratio. "
            f"{description}. "
            f"Aesthetic, soft lighting, skincare clinic atmosphere, clean and minimal"
        )
        return await self.generate(prompt, platform="instagram", style="instagram aesthetic photo")
