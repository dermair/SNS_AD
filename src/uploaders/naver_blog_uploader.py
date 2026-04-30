"""네이버 블로그 업로더 — 네이버 오픈 API로 블로그 글 게시."""

from __future__ import annotations

import asyncio
import webbrowser
from pathlib import Path
from urllib.parse import urlencode

import httpx

from src.core.config import APIKeys, CONFIG_DIR

NAVER_AUTH_URL = "https://nid.naver.com/oauth2.0/authorize"
NAVER_TOKEN_URL = "https://nid.naver.com/oauth2.0/token"
NAVER_BLOG_API = "https://openapi.naver.com/blog/writePost.json"
TOKEN_PATH = CONFIG_DIR / "naver_token.json"


class NaverBlogUploader:
    """네이버 오픈 API를 사용한 블로그 글 업로더.

    사전 요구사항:
    - 네이버 개발자 센터에서 애플리케이션 등록
    - Client ID / Client Secret 발급
    - 블로그 글쓰기 API 사용 신청
    """

    def __init__(self, api_keys: APIKeys | None = None):
        keys = api_keys or APIKeys.from_env()
        self._client_id = keys.naver_client_id
        self._client_secret = keys.naver_client_secret
        self._access_token = ""
        self._client = httpx.AsyncClient(timeout=60.0)

    def is_configured(self) -> bool:
        """네이버 API 설정이 되어 있는지 확인."""
        return bool(self._client_id and self._client_secret)

    def authenticate(self) -> bool:
        """OAuth 2.0 인증. 브라우저에서 네이버 로그인 후 코드 입력."""
        if not self.is_configured():
            print("[네이버] Client ID/Secret이 설정되지 않았습니다.")
            return False

        # 저장된 토큰이 있으면 로드
        if TOKEN_PATH.exists():
            import json
            data = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
            self._access_token = data.get("access_token", "")
            if self._access_token:
                return True

        # 인증 URL 생성
        params = {
            "response_type": "code",
            "client_id": self._client_id,
            "redirect_uri": "http://localhost:8080/callback",
            "state": "beauty_agent",
        }
        auth_url = f"{NAVER_AUTH_URL}?{urlencode(params)}"

        print(f"\n브라우저에서 네이버 로그인 페이지가 열립니다...")
        print(f"URL: {auth_url}\n")
        webbrowser.open(auth_url)

        code = input("로그인 후 리다이렉트된 URL의 'code' 값을 입력하세요: ").strip()
        if not code:
            return False

        # 토큰 교환
        import requests
        resp = requests.post(NAVER_TOKEN_URL, data={
            "grant_type": "authorization_code",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code": code,
            "state": "beauty_agent",
        })

        if resp.status_code != 200:
            print(f"[네이버] 토큰 발급 실패: {resp.text}")
            return False

        token_data = resp.json()
        self._access_token = token_data.get("access_token", "")

        if self._access_token:
            import json
            TOKEN_PATH.write_text(json.dumps(token_data, ensure_ascii=False), encoding="utf-8")
            return True

        return False

    async def upload_post(
        self,
        title: str,
        content: str,
        tags: list[str] | None = None,
    ) -> dict:
        """블로그 글을 게시한다.

        Args:
            title: 글 제목
            content: 글 본문 (HTML 형식)
            tags: 태그 리스트

        Returns:
            {"blog_url": "게시된 글 URL"}
        """
        if not self._access_token:
            raise RuntimeError("인증이 필요합니다. authenticate()를 먼저 호출하세요.")

        # 본문을 HTML로 변환 (줄바꿈 → <br>)
        html_content = content.replace("\n\n", "</p><p>").replace("\n", "<br>")
        html_content = f"<p>{html_content}</p>"

        data = {
            "title": title,
            "contents": html_content,
        }

        if tags:
            data["tag"] = ",".join(tags)

        response = await self._client.post(
            NAVER_BLOG_API,
            headers={
                "Authorization": f"Bearer {self._access_token}",
            },
            data=data,
        )

        if response.status_code == 401:
            # 토큰 만료 → 재인증 필요
            TOKEN_PATH.unlink(missing_ok=True)
            raise RuntimeError("토큰이 만료되었습니다. 다시 인증해주세요.")

        response.raise_for_status()
        result = response.json()

        return {
            "blog_url": result.get("message", {}).get("result", {}).get("blogUrl", ""),
            "log_no": result.get("message", {}).get("result", {}).get("logNo", ""),
        }

    async def close(self):
        await self._client.aclose()
