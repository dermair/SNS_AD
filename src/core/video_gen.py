"""영상 생성 클라이언트 — Kling AI API (JWT 인증, 비동기)."""

from __future__ import annotations

import asyncio
import time as time_mod
from datetime import datetime

import httpx
import jwt

from src.core.config import APIKeys, OUTPUT_DIR

KLING_API_BASE = "https://api.klingai.com/v1"


class VideoGenerator:
    """Kling AI를 사용한 영상 생성기."""

    def __init__(self, api_keys: APIKeys):
        self._access_key = api_keys.kling_key
        self._secret_key = api_keys.kling_secret
        self._client: httpx.AsyncClient | None = None

    def _generate_jwt_token(self) -> str:
        """Kling AI API용 JWT 토큰을 생성한다."""
        now = int(time_mod.time())
        payload = {
            "iss": self._access_key,
            "exp": now + 1800,  # 30분 만료
            "nbf": now - 5,
            "iat": now,
        }
        return jwt.encode(payload, self._secret_key, algorithm="HS256")

    async def _get_client(self) -> httpx.AsyncClient:
        """인증 토큰이 포함된 HTTP 클라이언트를 반환."""
        token = self._generate_jwt_token()
        if self._client:
            await self._client.aclose()
        self._client = httpx.AsyncClient(
            base_url=KLING_API_BASE,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )
        return self._client

    async def generate_video(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "9:16",
        platform: str = "youtube",
    ) -> dict:
        """영상을 생성한다.

        Args:
            prompt: 영상 설명 프롬프트
            duration: 영상 길이 (초)
            aspect_ratio: 화면 비율 (9:16 쇼츠/릴스, 16:9 일반)
            platform: 플랫폼 (youtube, instagram)

        Returns:
            {"task_id": 작업 ID, "status": 상태}
        """
        client = await self._get_client()

        payload = {
            "prompt": prompt,
            "duration": str(duration),
            "aspect_ratio": aspect_ratio,
            "model_name": "kling-v2-master",
        }

        response = await client.post("/videos/text2video", json=payload)
        response.raise_for_status()
        data = response.json()

        task_id = data.get("data", {}).get("task_id", "")

        return {
            "task_id": task_id,
            "status": "processing",
            "platform": platform,
            "prompt_used": prompt,
        }

    async def check_status(self, task_id: str) -> dict:
        """영상 생성 작업 상태를 확인한다."""
        client = await self._get_client()
        response = await client.get(f"/videos/text2video/{task_id}")
        response.raise_for_status()
        data = response.json()

        task_data = data.get("data", {})
        status = task_data.get("task_status", "processing")

        result = {"task_id": task_id, "status": status}

        if status == "completed":
            videos = task_data.get("task_result", {}).get("videos", [])
            if videos:
                result["video_url"] = videos[0].get("url", "")

        return result

    async def wait_and_download(
        self, task_id: str, platform: str = "youtube", max_wait: int = 300
    ) -> dict:
        """영상 생성 완료를 기다리고 다운로드한다."""
        elapsed = 0
        interval = 10

        while elapsed < max_wait:
            status = await self.check_status(task_id)

            if status["status"] == "completed" and "video_url" in status:
                video_url = status["video_url"]
                save_dir = OUTPUT_DIR / platform / "videos"
                save_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = save_dir / f"{platform}_{timestamp}.mp4"

                client = await self._get_client()
                video_response = await client.get(video_url)
                file_path.write_bytes(video_response.content)

                status["path"] = str(file_path)
                return status

            if status["status"] == "failed":
                return status

            await asyncio.sleep(interval)
            elapsed += interval

        return {"task_id": task_id, "status": "timeout"}

    async def generate_shorts(self, script: str, shop_name: str) -> dict:
        """유튜브 쇼츠 / 인스타 릴스용 세로 영상을 생성."""
        prompt = (
            f"Professional skincare clinic video for '{shop_name}'. "
            f"Vertical format, 9:16 ratio. "
            f"Scene: {script}. "
            f"Soft lighting, clean aesthetic, Korean skincare clinic atmosphere."
        )
        return await self.generate_video(prompt, duration=5, aspect_ratio="9:16")

    async def close(self):
        if self._client:
            await self._client.aclose()
