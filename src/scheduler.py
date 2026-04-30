"""콘텐츠 스케줄러 — 요일별 자동 콘텐츠 생성 + 업로드."""

from __future__ import annotations

import asyncio
import json
import random
from datetime import datetime
from pathlib import Path

import yaml

from src.core.config import APIKeys, ShopProfile, CONFIG_DIR, OUTPUT_DIR
from src.core.llm import LLMClient, LLMProvider

SCHEDULE_PATH = CONFIG_DIR / "schedule.yaml"
LOG_DIR = OUTPUT_DIR / "logs"

DAY_MAP = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday",
    5: "saturday",
    6: "sunday",
}


class Scheduler:
    """요일별 콘텐츠 자동 생성 + 업로드 스케줄러."""

    def __init__(self):
        self.config = self._load_config()
        self.shop = ShopProfile.from_yaml()
        self.api_keys = APIKeys.from_env()

    def _load_config(self) -> dict:
        if not SCHEDULE_PATH.exists():
            raise FileNotFoundError(f"스케줄 설정 파일이 없습니다: {SCHEDULE_PATH}")
        with open(SCHEDULE_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _save_config(self):
        with open(SCHEDULE_PATH, "w", encoding="utf-8") as f:
            yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)

    def get_today_task(self, day_override: str | None = None) -> dict:
        """오늘(또는 지정된 요일)의 작업을 반환."""
        if day_override:
            day_name = day_override.lower()
        else:
            day_name = DAY_MAP[datetime.now().weekday()]

        schedule = self.config.get("schedule", {})
        task_info = schedule.get(day_name, {"task": "off"})

        return {
            "day": day_name,
            "task": task_info.get("task", "off"),
            "time": task_info.get("time", "09:00"),
        }

    def get_next_topic(self) -> str:
        """주제 큐에서 다음 주제를 꺼낸다. 없으면 빈 문자열."""
        queue = self.config.get("topic_queue", [])
        if queue:
            topic = queue.pop(0)
            self._save_config()
            return topic
        return ""

    def add_topic(self, topic: str):
        """주제 큐에 새 주제를 추가."""
        if "topic_queue" not in self.config:
            self.config["topic_queue"] = []
        self.config["topic_queue"].append(topic)
        self._save_config()

    async def generate_auto_topic(self) -> str:
        """AI가 시술 메뉴 기반으로 주제를 자동 생성."""
        llm = LLMClient(self.api_keys)
        services = [s.name for s in self.shop.services]
        service = random.choice(services)

        prompt = (
            f"피부관리실 '{self.shop.name}'의 '{service}' 시술에 대한 "
            f"블로그/SNS 콘텐츠 주제를 하나만 짧게 제안해주세요. "
            f"타겟: {self.shop.tone.target_audience}. "
            f"10자~20자 이내의 주제만 답하세요."
        )

        topic = await llm.generate(
            prompt=prompt,
            provider=LLMProvider.CLAUDE,
            system="콘텐츠 주제를 짧게 제안하는 역할입니다. 주제만 답하세요.",
            max_tokens=50,
            temperature=0.9,
        )
        return topic.strip().strip('"').strip("'")

    async def notify(self, day_override: str | None = None):
        """오늘의 작업을 텔레그램으로 알린다 (승인 전 미리보기)."""
        from src.notifier import TelegramNotifier

        task_info = self.get_today_task(day_override)
        task = task_info["task"]
        day = task_info["day"]

        if task == "off":
            return {"day": day, "task": "off", "status": "skip"}

        # 주제 미리 확인 (큐에서 꺼내지 않고 peek만)
        queue = self.config.get("topic_queue", [])
        topic = queue[0] if queue else "(AI 자동 생성 예정)"

        notifier = TelegramNotifier(self.api_keys)
        if notifier.is_configured():
            sent = await notifier.send_schedule_preview(day, task, topic)
            await notifier.close()
            if sent:
                return {"day": day, "task": task, "topic": topic, "status": "notified"}
            return {"day": day, "task": task, "topic": topic, "status": "send_failed"}

        return {"day": day, "task": task, "topic": topic, "status": "not_configured"}

    async def auto_run(self, day_override: str | None = None):
        """알림 + 자동 생성 + 텔레그램 결과 전송 (스케줄러용)."""
        from src.notifier import TelegramNotifier

        task_info = self.get_today_task(day_override)
        task = task_info["task"]
        day = task_info["day"]

        if task == "off":
            return {"day": day, "task": "off", "status": "skip"}

        notifier = TelegramNotifier(self.api_keys)

        # 1) 시작 알림
        if notifier.is_configured():
            day_kr = {"monday":"월","tuesday":"화","wednesday":"수","thursday":"목","friday":"금","saturday":"토","sunday":"일"}.get(day, day)
            task_kr = {"youtube_shorts":"유튜브 쇼츠","blog":"네이버 블로그","instagram_carousel":"인스타 캐러셀","instagram_reels":"인스타 릴스"}.get(task, task)
            await notifier.send_to_me(
                title="콘텐츠 생성 시작",
                description=f"{day_kr}요일 {task_kr} 작업을 시작합니다...",
            )

        # 2) 콘텐츠 자동 생성
        result = await self.run(day_override, send_result=False)

        # 3) 결과를 텔레그램으로 전송
        if notifier.is_configured() and result.get("status") == "generated":
            file_path = result.get("file", "")
            if file_path:
                from pathlib import Path
                fp = Path(file_path)
                if fp.exists() and fp.suffix in (".md", ".txt"):
                    content = fp.read_text(encoding="utf-8")
                    await notifier.send_content_preview(content, task.split("_")[0] if "_" in task else task)

            await notifier.send_to_me(
                title="콘텐츠 생성 완료",
                description=(
                    f"주제: {result.get('topic', '')}\n"
                    f"파일: {file_path}\n\n"
                    f"확인 후 업로드하세요:\n"
                    f"python -m src.main upload -p {self._task_to_platform(task)}"
                ),
            )

        elif notifier.is_configured():
            await notifier.send_to_me(
                title="콘텐츠 생성 알림",
                description=f"결과: {result.get('status', 'unknown')}",
            )

        if notifier.is_configured():
            await notifier.close()

        return result

    @staticmethod
    def _task_to_platform(task: str) -> str:
        return {"youtube_shorts": "youtube", "blog": "blog", "instagram_carousel": "instagram", "instagram_reels": "instagram"}.get(task, task)

    async def run(self, day_override: str | None = None, send_result: bool = True):
        """오늘의 스케줄 작업을 실행."""
        task_info = self.get_today_task(day_override)
        task = task_info["task"]
        day = task_info["day"]

        if task == "off":
            self._log(day, "off", "휴무일")
            return {"day": day, "task": "off", "status": "skip"}

        # 주제 결정
        topic = self.get_next_topic()
        if not topic:
            auto = self.config.get("auto_topic", {})
            if auto.get("enabled", True):
                topic = await self.generate_auto_topic()
            else:
                self._log(day, task, "주제 없음 - 건너뜀")
                return {"day": day, "task": task, "status": "no_topic"}

        print(f"[스케줄] {day} | 작업: {task} | 주제: {topic}")

        # 작업 실행
        result = {"day": day, "task": task, "topic": topic}

        if task == "youtube_shorts":
            result.update(await self._run_youtube_shorts(topic))
        elif task == "blog":
            result.update(await self._run_blog(topic))
        elif task == "instagram_carousel":
            result.update(await self._run_instagram_carousel(topic))
        elif task == "instagram_reels":
            result.update(await self._run_instagram_reels(topic))

        self._log(day, task, topic, result.get("status", "done"))

        # 완료 알림
        if send_result:
            from src.notifier import TelegramNotifier
            notifier = TelegramNotifier(self.api_keys)
            if notifier.is_configured():
                await notifier.send_result(
                    day, task, topic,
                    result.get("status", ""),
                    result.get("file", ""),
                )
                await notifier.close()

        return result

    async def _run_blog(self, topic: str) -> dict:
        """블로그 글 생성 + 네이버 업로드."""
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

    async def _run_youtube_shorts(self, topic: str) -> dict:
        """쇼츠 영상 생성 (input/ 폴더 사진 사용)."""
        from src.utils.media import collect_images
        from src.core.video_editor import VideoEditor
        from src.agents.shorts_agent import ShortsAgent

        images = collect_images("./input/")
        if not images:
            return {"status": "no_images"}

        llm = LLMClient(self.api_keys)
        agent = ShortsAgent(llm, self.shop, VideoEditor())

        script = await agent.generate_script(images, topic=topic, mode="slideshow")
        result = await agent.generate_video(script)

        return {"status": "generated", "file": result.video_path}

    async def _run_instagram_carousel(self, topic: str) -> dict:
        """인스타 캐러셀 콘텐츠 생성."""
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

    async def _run_instagram_reels(self, topic: str) -> dict:
        """릴스 영상 생성 (input/ 폴더 사진 사용)."""
        from src.utils.media import collect_images
        from src.core.video_editor import VideoEditor
        from src.agents.shorts_agent import ShortsAgent

        images = collect_images("./input/")
        if not images:
            return {"status": "no_images"}

        llm = LLMClient(self.api_keys)
        agent = ShortsAgent(llm, self.shop, VideoEditor())

        script = await agent.generate_script(images, topic=topic, mode="narration")
        result = await agent.generate_video(script, tts_provider="edge-tts")

        return {"status": "generated", "file": result.video_path}

    def _log(self, day: str, task: str, topic: str, status: str = ""):
        """실행 로그를 저장."""
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_file = LOG_DIR / f"schedule_{datetime.now().strftime('%Y%m')}.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {day} | {task} | {topic} | {status}\n"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line)

    def get_status(self) -> dict:
        """현재 스케줄 상태를 반환."""
        today = self.get_today_task()
        queue = self.config.get("topic_queue", [])
        auto = self.config.get("auto_topic", {}).get("enabled", True)

        # 최근 로그
        log_file = LOG_DIR / f"schedule_{datetime.now().strftime('%Y%m')}.log"
        recent_logs = []
        if log_file.exists():
            lines = log_file.read_text(encoding="utf-8").splitlines()
            recent_logs = lines[-5:] if len(lines) >= 5 else lines

        return {
            "today": today,
            "queue_count": len(queue),
            "queue_preview": queue[:3],
            "auto_topic": auto,
            "recent_logs": recent_logs,
        }
