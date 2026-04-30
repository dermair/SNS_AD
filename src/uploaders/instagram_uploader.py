"""Instagram 업로더 — Instagram Graph API로 피드/릴스 업로드."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import httpx

from src.core.config import APIKeys


class InstagramUploader:
    """Instagram Graph API를 사용한 콘텐츠 업로더.

    사전 요구사항:
    - Instagram Business 또는 Creator 계정
    - Facebook Page와 연결
    - Meta for Developers 앱 등록
    - instagram_business_content_publish 권한
    """

    def __init__(self, api_keys: APIKeys | None = None):
        keys = api_keys or APIKeys.from_env()
        self._access_token = keys.instagram_token
        self._ig_user_id = keys.instagram_user_id
        self._client = httpx.AsyncClient(
            base_url="https://graph.facebook.com/v21.0",
            timeout=120.0,
        )

    def is_configured(self) -> bool:
        """Instagram API 설정이 되어 있는지 확인."""
        return bool(self._access_token and self._ig_user_id)

    async def upload_image(
        self,
        image_url: str,
        caption: str = "",
    ) -> dict:
        """이미지를 Instagram 피드에 업로드한다.

        Args:
            image_url: 이미지의 공개 URL (Instagram이 다운로드 가능해야 함)
            caption: 캡션 + 해시태그

        Returns:
            {"media_id": "xxx", "status": "published"}
        """
        # 1단계: 미디어 컨테이너 생성
        container = await self._client.post(
            f"/{self._ig_user_id}/media",
            params={
                "image_url": image_url,
                "caption": caption,
                "access_token": self._access_token,
            },
        )
        container.raise_for_status()
        creation_id = container.json().get("id")

        # 2단계: 발행
        publish = await self._client.post(
            f"/{self._ig_user_id}/media_publish",
            params={
                "creation_id": creation_id,
                "access_token": self._access_token,
            },
        )
        publish.raise_for_status()
        media_id = publish.json().get("id")

        return {"media_id": media_id, "status": "published"}

    async def upload_reels(
        self,
        video_url: str,
        caption: str = "",
    ) -> dict:
        """릴스(영상)를 Instagram에 업로드한다.

        Args:
            video_url: 영상의 공개 URL
            caption: 캡션 + 해시태그

        Returns:
            {"media_id": "xxx", "status": "published"}
        """
        # 1단계: 릴스 컨테이너 생성
        container = await self._client.post(
            f"/{self._ig_user_id}/media",
            params={
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "access_token": self._access_token,
            },
        )
        container.raise_for_status()
        creation_id = container.json().get("id")

        # 2단계: 처리 완료 대기
        await self._wait_for_processing(creation_id)

        # 3단계: 발행
        publish = await self._client.post(
            f"/{self._ig_user_id}/media_publish",
            params={
                "creation_id": creation_id,
                "access_token": self._access_token,
            },
        )
        publish.raise_for_status()
        media_id = publish.json().get("id")

        return {"media_id": media_id, "status": "published"}

    async def upload_carousel(
        self,
        image_urls: list[str],
        caption: str = "",
    ) -> dict:
        """캐러셀(여러 이미지)을 Instagram에 업로드한다.

        Args:
            image_urls: 이미지 공개 URL 리스트 (최대 10개)
            caption: 캡션 + 해시태그
        """
        # 1단계: 각 이미지를 개별 컨테이너로 생성
        children_ids = []
        for url in image_urls[:10]:
            resp = await self._client.post(
                f"/{self._ig_user_id}/media",
                params={
                    "image_url": url,
                    "is_carousel_item": "true",
                    "access_token": self._access_token,
                },
            )
            resp.raise_for_status()
            children_ids.append(resp.json().get("id"))

        # 2단계: 캐러셀 컨테이너 생성
        container = await self._client.post(
            f"/{self._ig_user_id}/media",
            params={
                "media_type": "CAROUSEL",
                "children": ",".join(children_ids),
                "caption": caption,
                "access_token": self._access_token,
            },
        )
        container.raise_for_status()
        creation_id = container.json().get("id")

        # 3단계: 발행
        publish = await self._client.post(
            f"/{self._ig_user_id}/media_publish",
            params={
                "creation_id": creation_id,
                "access_token": self._access_token,
            },
        )
        publish.raise_for_status()
        media_id = publish.json().get("id")

        return {"media_id": media_id, "status": "published"}

    async def _wait_for_processing(self, creation_id: str, max_wait: int = 120):
        """영상 처리 완료를 기다린다."""
        elapsed = 0
        while elapsed < max_wait:
            resp = await self._client.get(
                f"/{creation_id}",
                params={
                    "fields": "status_code",
                    "access_token": self._access_token,
                },
            )
            status = resp.json().get("status_code")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise RuntimeError(f"Instagram 영상 처리 실패: {resp.json()}")
            await asyncio.sleep(5)
            elapsed += 5

        raise TimeoutError("Instagram 영상 처리 시간 초과")

    async def close(self):
        await self._client.aclose()
