"""YouTube 업로더 — YouTube Data API v3으로 영상 업로드."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from src.core.config import CONFIG_DIR

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_PATH = CONFIG_DIR / "youtube_token.json"
CLIENT_SECRETS_PATH = CONFIG_DIR / "client_secrets.json"


class YouTubeUploader:
    """YouTube Data API v3를 사용한 영상 업로더."""

    def __init__(self):
        self._service = None

    def authenticate(self) -> bool:
        """OAuth 2.0 인증. 최초 1회 브라우저 인증, 이후 토큰 자동 갱신."""
        if not CLIENT_SECRETS_PATH.exists():
            print(f"[YouTube] client_secrets.json이 없습니다: {CLIENT_SECRETS_PATH}")
            print("  Google Cloud Console → API 및 서비스 → 사용자 인증 정보 → OAuth 2.0 클라이언트 ID 생성")
            print(f"  다운로드한 JSON 파일을 {CLIENT_SECRETS_PATH} 에 저장하세요.")
            return False

        creds = None

        # 저장된 토큰이 있으면 로드
        if TOKEN_PATH.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

        # 토큰이 없거나 만료됐으면 갱신/재인증
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CLIENT_SECRETS_PATH), SCOPES
                )
                creds = flow.run_local_server(port=8080)

            # 토큰 저장
            TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

        self._service = build("youtube", "v3", credentials=creds)
        return True

    async def upload_video(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: list[str] | None = None,
        category_id: str = "22",
        privacy: str = "private",
        is_shorts: bool = False,
    ) -> dict:
        """영상을 YouTube에 업로드한다.

        Args:
            video_path: 영상 파일 경로
            title: 영상 제목
            description: 영상 설명
            tags: 태그 리스트
            category_id: 카테고리 ID (22 = People & Blogs)
            privacy: 공개 설정 (private/unlisted/public)
            is_shorts: True면 제목에 #Shorts 추가

        Returns:
            {"video_id": "xxx", "url": "https://youtube.com/watch?v=xxx"}
        """
        if not self._service:
            raise RuntimeError("인증이 필요합니다. authenticate()를 먼저 호출하세요.")

        if not Path(video_path).exists():
            raise FileNotFoundError(f"영상 파일을 찾을 수 없습니다: {video_path}")

        # 쇼츠 태그 추가
        if is_shorts and "#Shorts" not in title:
            title = f"{title} #Shorts"

        body = {
            "snippet": {
                "title": title[:100],  # YouTube 제목 최대 100자
                "description": description[:5000],  # 최대 5000자
                "tags": tags or [],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=10 * 1024 * 1024,  # 10MB 청크
        )

        request = self._service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        # 업로드 실행 (동기 → to_thread)
        response = await asyncio.to_thread(self._execute_upload, request)

        video_id = response.get("id", "")
        return {
            "video_id": video_id,
            "url": f"https://youtube.com/watch?v={video_id}",
            "title": title,
            "privacy": privacy,
        }

    def _execute_upload(self, request) -> dict:
        """resumable 업로드를 실행한다."""
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"  업로드 진행: {int(status.progress() * 100)}%")
        return response
