"""텔레그램 봇 알림 — 양방향 소통, 토큰 영구, 사진 전송 가능."""

from __future__ import annotations

from pathlib import Path

import httpx

from src.core.config import APIKeys


class TelegramNotifier:
    """텔레그램 봇을 사용한 알림 모듈.

    특징:
    - 토큰 영구 (재인증 불필요)
    - 양방향 통신 (메시지 수신 가능)
    - 사진/파일 전송 가능
    """

    def __init__(self, api_keys: APIKeys | None = None):
        keys = api_keys or APIKeys.from_env()
        self._token = keys.telegram_bot_token
        self._chat_id = keys.telegram_chat_id
        self._base_url = f"https://api.telegram.org/bot{self._token}"
        self._client = httpx.AsyncClient(timeout=30.0)

    def is_configured(self) -> bool:
        return bool(self._token and self._chat_id)

    async def send_message(self, text: str, parse_mode: str = "") -> bool:
        """텍스트 메시지를 보낸다."""
        data = {"chat_id": self._chat_id, "text": text}
        if parse_mode:
            data["parse_mode"] = parse_mode

        # 텔레그램 메시지 최대 4096자 → 분할 전송
        if len(text) > 4000:
            chunks = []
            while text:
                chunks.append(text[:4000])
                text = text[4000:]
            for chunk in chunks:
                data["text"] = chunk
                resp = await self._client.post(f"{self._base_url}/sendMessage", json=data)
                if not resp.json().get("ok"):
                    return False
            return True

        resp = await self._client.post(f"{self._base_url}/sendMessage", json=data)
        return resp.json().get("ok", False)

    async def send_photo(self, photo_path: str, caption: str = "") -> bool:
        """사진을 보낸다."""
        p = Path(photo_path)
        if not p.exists():
            return False

        with open(p, "rb") as f:
            resp = await self._client.post(
                f"{self._base_url}/sendPhoto",
                data={"chat_id": self._chat_id, "caption": caption[:1024]},
                files={"photo": (p.name, f, "image/jpeg")},
            )
        return resp.json().get("ok", False)

    async def send_file(self, file_path: str, caption: str = "") -> bool:
        """파일을 보낸다 (영상, 문서 등)."""
        p = Path(file_path)
        if not p.exists():
            return False

        with open(p, "rb") as f:
            resp = await self._client.post(
                f"{self._base_url}/sendDocument",
                data={"chat_id": self._chat_id, "caption": caption[:1024]},
                files={"document": (p.name, f)},
            )
        return resp.json().get("ok", False)

    async def get_new_messages(self, offset: int = 0) -> list[dict]:
        """새 메시지를 가져온다 (양방향 통신)."""
        params = {"offset": offset, "timeout": 5}
        resp = await self._client.get(f"{self._base_url}/getUpdates", params=params)
        data = resp.json()
        if data.get("ok"):
            return data.get("result", [])
        return []

    # ── 스케줄러 연동 메서드 ──

    async def send_to_me(self, title: str, description: str, **kwargs) -> bool:
        """호환용 — 기존 코드에서 호출하는 메서드."""
        text = f"📌 {title}\n\n{description}"
        return await self.send_message(text)

    async def send_schedule_preview(self, day: str, task: str, topic: str) -> bool:
        """스케줄 실행 전 미리보기 알림."""
        day_kr = {"monday":"월","tuesday":"화","wednesday":"수","thursday":"목","friday":"금","saturday":"토","sunday":"일"}.get(day, day)
        task_kr = {"youtube_shorts":"유튜브 쇼츠","blog":"네이버 블로그","instagram_carousel":"인스타 캐러셀","instagram_reels":"인스타 릴스"}.get(task, task)

        text = (
            f"📌 피부관리실 홍보 에이전트\n\n"
            f"오늘({day_kr}요일) 작업: {task_kr}\n"
            f"주제: {topic}\n\n"
            f"콘텐츠 생성을 시작합니다..."
        )
        return await self.send_message(text)

    async def send_result(self, day: str, task: str, topic: str, status: str, file_path: str = "") -> bool:
        """작업 완료 결과를 알린다."""
        day_kr = {"monday":"월","tuesday":"화","wednesday":"수","thursday":"목","friday":"금","saturday":"토","sunday":"일"}.get(day, day)
        task_kr = {"youtube_shorts":"유튜브 쇼츠","blog":"네이버 블로그","instagram_carousel":"인스타 캐러셀","instagram_reels":"인스타 릴스"}.get(task, task)

        if status == "generated":
            content_preview = ""
            if file_path:
                fp = Path(file_path)
                if fp.exists() and fp.suffix in (".md", ".txt"):
                    text = fp.read_text(encoding="utf-8")
                    content_preview = text[:3000] if len(text) > 3000 else text

            msg = f"✅ {day_kr}요일 {task_kr} 생성 완료!\n주제: {topic}\n\n"
            if content_preview:
                msg += f"{content_preview}\n\n"
            msg += "검수 후 업로드 해주세요."
        else:
            msg = f"⚠️ {day_kr}요일 {task_kr} 결과: {status}"

        return await self.send_message(msg)

    async def send_content_preview(self, content_text: str, platform: str = "") -> bool:
        """생성된 콘텐츠를 전송."""
        platform_kr = {"blog":"블로그","instagram":"인스타그램","youtube":"유튜브"}.get(platform, platform)
        text = f"📄 {platform_kr} 콘텐츠\n\n{content_text}"
        return await self.send_message(text)

    async def close(self):
        await self._client.aclose()
