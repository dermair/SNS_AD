"""텔레그램 봇 대화형 모드 — 매일 아침 질문 → 답변 → 콘텐츠 생성."""

from __future__ import annotations

import asyncio
from pathlib import Path

from src.core.config import APIKeys, ShopProfile, OUTPUT_DIR
from src.core.llm import LLMClient
from src.core.video_editor import VideoEditor
from src.notifier import TelegramNotifier


MORNING_MESSAGE = """☀️ 좋은 아침이에요!

오늘 만들 홍보물을 알려주세요.

예시:
• 블로그 - 여드름 관리 후기
• 인스타 캐러셀 - 트러블과 호르몬
• 인스타 릴스 - 모공 케어 전후
• 유튜브 쇼츠 - 수분 관리 과정
• 전체 - 리프팅 관리 소개

또는 자유롭게 적어주세요!"""


class TelegramBot:
    """텔레그램 대화형 봇 — 질문 → 답변 → 콘텐츠 생성."""

    def __init__(self):
        self.api_keys = APIKeys.from_env()
        self.shop = ShopProfile.from_yaml()
        self.notifier = TelegramNotifier(self.api_keys)
        self._last_update_id = 0

    async def send_morning_question(self):
        """아침 인사 + 질문을 보낸다."""
        await self.notifier.send_message(MORNING_MESSAGE)

    async def wait_for_reply(self, timeout: int = 3600) -> str | None:
        """사용자 답장을 기다린다 (최대 timeout초)."""
        import httpx

        token = self.api_keys.telegram_bot_token
        base_url = f"https://api.telegram.org/bot{token}"
        chat_id = self.api_keys.telegram_chat_id

        elapsed = 0
        interval = 5

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 기존 메시지 건너뛰기
            resp = await client.get(f"{base_url}/getUpdates", params={"offset": -1})
            data = resp.json()
            if data.get("result"):
                self._last_update_id = data["result"][-1]["update_id"] + 1

            # 새 메시지 대기
            while elapsed < timeout:
                resp = await client.get(f"{base_url}/getUpdates", params={
                    "offset": self._last_update_id,
                    "timeout": 10,
                })
                data = resp.json()

                for update in data.get("result", []):
                    self._last_update_id = update["update_id"] + 1
                    msg = update.get("message", {})
                    if str(msg.get("chat", {}).get("id")) == str(chat_id):
                        text = msg.get("text", "")
                        if text:
                            return text

                elapsed += interval

        return None

    def parse_request(self, text: str) -> dict:
        """사용자 답장을 파싱하여 작업 종류와 주제를 추출한다."""
        text = text.strip()

        # "블로그 - 주제" 형식 파싱
        platform = "all"
        topic = text

        # 긴 키워드를 먼저 매칭 (순서 중요)
        mappings = [
            ("인스타 캐러셀", "instagram_carousel"),
            ("인스타캐러셀", "instagram_carousel"),
            ("인스타 릴스", "instagram_reels"),
            ("인스타릴스", "instagram_reels"),
            ("유튜브 쇼츠", "youtube_shorts"),
            ("카드뉴스", "instagram_carousel"),
            ("캐러셀", "instagram_carousel"),
            ("블로그", "blog"),
            ("릴스", "instagram_reels"),
            ("유튜브", "youtube_shorts"),
            ("쇼츠", "youtube_shorts"),
            ("전체", "all"),
        ]

        for keyword, plat in mappings:
            if text.startswith(keyword):
                platform = plat
                # "블로그에", "블로그로" 등 조사 제거 후 주제 추출
                rest = text[len(keyword):]
                rest = rest.lstrip("에으로에서의는을를이가 -:").strip()
                topic = rest
                break

        if not topic:
            topic = self.shop.name

        return {"platform": platform, "topic": topic}

    async def execute(self, request: dict):
        """파싱된 요청을 실행한다."""
        platform = request["platform"]
        topic = request["topic"]

        platform_kr = {
            "blog": "블로그",
            "instagram_carousel": "인스타 캐러셀",
            "instagram_reels": "인스타 릴스",
            "youtube_shorts": "유튜브 쇼츠",
            "all": "전체 플랫폼",
        }.get(platform, platform)

        await self.notifier.send_message(f"🔄 {platform_kr} 콘텐츠 생성 중...\n주제: {topic}")

        try:
            if platform == "blog":
                result = await self._run_blog(topic)
            elif platform == "instagram_carousel":
                result = await self._run_instagram(topic)
            elif platform == "instagram_reels":
                result = await self._run_reels(topic)
            elif platform == "youtube_shorts":
                result = await self._run_shorts(topic)
            elif platform == "all":
                result = await self._run_all(topic)
            else:
                result = await self._run_all(topic)

            # 결과 전송
            if result.get("file"):
                fp = Path(result["file"])
                if fp.exists() and fp.suffix in (".md", ".txt"):
                    content = fp.read_text(encoding="utf-8")
                    await self.notifier.send_content_preview(content, platform)

            await self.notifier.send_message(f"✅ {platform_kr} 생성 완료!\n파일: {result.get('file', 'N/A')}")

        except Exception as e:
            await self.notifier.send_message(f"❌ 생성 실패: {e}")

    async def _run_blog(self, topic: str) -> dict:
        from src.agents.orchestrator import Orchestrator
        from src.models.content import ContentRequest, Platform
        from src.platforms.blog import BlogFormatter

        orchestrator = Orchestrator(self.shop, self.api_keys)
        request = ContentRequest(topic=topic, platforms=[Platform.BLOG])
        result = await orchestrator.generate(request)

        blog = result.get_blog()
        if blog:
            path = BlogFormatter().save(blog)
            return {"status": "generated", "file": path}
        return {"status": "failed"}

    async def _run_instagram(self, topic: str) -> dict:
        from src.agents.orchestrator import Orchestrator
        from src.models.content import ContentRequest, Platform
        from src.platforms.instagram import InstagramFormatter

        orchestrator = Orchestrator(self.shop, self.api_keys)
        request = ContentRequest(topic=topic, platforms=[Platform.INSTAGRAM])
        result = await orchestrator.generate(request)

        insta = result.get_instagram()
        if insta:
            path = InstagramFormatter().save(insta)
            return {"status": "generated", "file": path}
        return {"status": "failed"}

    async def _run_reels(self, topic: str) -> dict:
        from src.utils.media import collect_images
        from src.agents.shorts_agent import ShortsAgent

        images = collect_images("./input/")
        if not images:
            await self.notifier.send_message("⚠️ input/ 폴더에 사진이 없습니다.")
            return {"status": "no_images"}

        llm = LLMClient(self.api_keys)
        agent = ShortsAgent(llm, self.shop, VideoEditor())
        script = await agent.generate_script(images, topic=topic, mode="narration")
        result = await agent.generate_video(script, tts_provider="edge-tts")
        return {"status": "generated", "file": result.video_path}

    async def _run_shorts(self, topic: str) -> dict:
        from src.utils.media import collect_images
        from src.agents.shorts_agent import ShortsAgent

        images = collect_images("./input/")
        if not images:
            await self.notifier.send_message("⚠️ input/ 폴더에 사진이 없습니다.")
            return {"status": "no_images"}

        llm = LLMClient(self.api_keys)
        agent = ShortsAgent(llm, self.shop, VideoEditor())
        script = await agent.generate_script(images, topic=topic, mode="slideshow")
        result = await agent.generate_video(script)
        return {"status": "generated", "file": result.video_path}

    async def _run_all(self, topic: str) -> dict:
        from src.agents.orchestrator import Orchestrator
        from src.models.content import ContentRequest, Platform
        from src.platforms.blog import BlogFormatter
        from src.platforms.instagram import InstagramFormatter
        from src.platforms.youtube import YouTubeFormatter

        orchestrator = Orchestrator(self.shop, self.api_keys)
        request = ContentRequest(topic=topic)
        result = await orchestrator.generate(request)

        files = []
        blog = result.get_blog()
        if blog:
            files.append(BlogFormatter().save(blog))
        insta = result.get_instagram()
        if insta:
            files.append(InstagramFormatter().save(insta))
        yt = result.get_youtube()
        if yt:
            files.append(YouTubeFormatter().save(yt))

        return {"status": "generated", "file": files[0] if files else ""}

    async def run_morning(self):
        """아침 루틴: 질문 → 답장 대기 → 실행."""
        await self.send_morning_question()

        reply = await self.wait_for_reply(timeout=7200)  # 2시간 대기

        if not reply:
            await self.notifier.send_message("⏰ 2시간 동안 답장이 없어서 오늘은 건너뛸게요.")
            return

        request = self.parse_request(reply)
        await self.execute(request)
        await self.notifier.close()
