"""쇼츠/릴스 자동 생성 에이전트 — 사진 → 영상 자동 편집."""

from __future__ import annotations

import json
from pathlib import Path

from src.core.config import ShopProfile, OUTPUT_DIR
from src.core.llm import LLMClient, LLMProvider
from src.core.video_editor import VideoEditor
from src.utils.media import collect_images, generate_tts
from src.models.content import ShortsContent


SHORTS_SUBTITLE_SYSTEM = """너는 유튜브 쇼츠/인스타 릴스용 자막을 작성하는 전문가야.
주어진 사진 설명과 주제를 바탕으로 60초 이내 영상의 자막을 생성해.

규칙:
- 사진 장수에 맞게 자막을 나눠서 작성
- 각 자막은 2~4초 동안 표시
- 짧고 임팩트 있는 문장
- 감성적이면서 정보가 담긴 톤
- 첫 자막은 후킹 (호기심 유발)
- 마지막 자막은 CTA (팔로우, 문의 유도)

응답 형식 (JSON):
{
  "title": "영상 제목 (짧게)",
  "description": "영상 설명 (1-2문장)",
  "tags": ["태그1", "태그2", ...],
  "segments": [
    {"start": 0, "end": 4, "text": "첫 번째 자막"},
    {"start": 4, "end": 8, "text": "두 번째 자막"},
    ...
  ],
  "narration": "전체 나레이션 텍스트 (TTS용, 자연스러운 한국어)"
}"""

SHORTS_SUBTITLE_USER = """{shop_context}

사진 {image_count}장으로 {mode} 영상을 만듭니다.
주제: {topic}

사진당 약 {duration_per_image}초씩 표시됩니다.
총 영상 길이: 약 {total_duration}초

각 사진에 맞는 자막과 나레이션을 생성해주세요. JSON 형식으로 응답하세요."""


class ShortsAgent:
    """유튜브 쇼츠/인스타 릴스 자동 생성 에이전트."""

    def __init__(
        self,
        llm: LLMClient,
        shop: ShopProfile,
        video_editor: VideoEditor | None = None,
    ):
        self.llm = llm
        self.shop = shop
        self.video_editor = video_editor or VideoEditor()

    async def generate_script(
        self,
        image_paths: list[str | Path],
        topic: str = "",
        mode: str = "slideshow",
    ) -> ShortsContent:
        """1단계: 스크립트만 생성한다 (영상 제작 전 검수용).

        Returns:
            ShortsContent (video_path는 None, 텍스트만 채워짐)
        """
        if not image_paths:
            raise ValueError("사진이 없습니다. --images 경로를 확인하세요.")

        image_count = len(image_paths)
        duration_per_image = min(8.0, 60.0 / image_count)
        total_duration = duration_per_image * image_count

        text_data = await self._generate_text(
            image_count=image_count,
            topic=topic or self.shop.name,
            mode=mode,
            duration_per_image=duration_per_image,
            total_duration=total_duration,
        )

        return ShortsContent(
            title=text_data.get("title", ""),
            description=text_data.get("description", ""),
            tags=text_data.get("tags", []),
            subtitle_segments=text_data.get("segments", []),
            narration_text=text_data.get("narration", ""),
            video_path=None,
            mode=mode,
            source_images=[str(p) for p in image_paths],
        )

    async def generate_video(
        self,
        script: ShortsContent,
        bgm_path: str | None = None,
        tts_provider: str = "edge-tts",
    ) -> ShortsContent:
        """2단계: 확인된 스크립트로 영상을 생성한다."""
        image_count = len(script.source_images)
        duration_per_image = min(8.0, 60.0 / image_count)

        # 슬라이드쇼 영상 생성
        slideshow = await self.video_editor.create_slideshow(
            image_paths=script.source_images,
            duration_per_image=duration_per_image,
            max_duration=60.0,
        )
        video_path = slideshow["path"]

        # 자막 오버레이
        if script.subtitle_segments:
            sub_result = await self.video_editor.add_subtitles(
                video_path=video_path,
                subtitle_segments=script.subtitle_segments,
            )
            video_path = sub_result["path"]

        # 모드별 오디오 처리
        if script.mode == "narration" and script.narration_text:
            tts_path = await generate_tts(
                text=script.narration_text,
                provider=tts_provider,
            )
            narr_result = await self.video_editor.add_narration(
                video_path=video_path,
                narration_path=str(tts_path),
            )
            video_path = narr_result["path"]
        elif script.mode == "slideshow" and bgm_path:
            bgm_result = await self.video_editor.add_bgm(
                video_path=video_path,
                bgm_path=bgm_path,
            )
            video_path = bgm_result["path"]

        script.video_path = video_path
        return script

    async def export_for_capcut(
        self,
        script: ShortsContent,
        bgm_path: str | None = None,
        tts_provider: str = "edge-tts",
    ) -> dict:
        """CapCut 편집용 개별 소스를 내보낸다.

        Returns:
            {"capcut_dir": 폴더 경로, "photos": [], "srt": 경로, "narration": 경로, "bgm": 경로}
        """
        import shutil
        from datetime import datetime
        from src.utils.media import resize_for_shorts

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        capcut_dir = OUTPUT_DIR / "youtube" / "capcut" / timestamp
        photos_dir = capcut_dir / "photos"
        photos_dir.mkdir(parents=True, exist_ok=True)

        result = {"capcut_dir": str(capcut_dir)}

        # 1) 사진 리사이즈 + 번호 매기기
        photo_paths = []
        for i, img_path in enumerate(script.source_images, 1):
            from pathlib import Path
            src = Path(img_path)
            if src.exists():
                resized = resize_for_shorts(src)
                dst = photos_dir / f"{i:02d}_{src.name}"
                shutil.copy2(str(resized), str(dst))
                photo_paths.append(str(dst))
        result["photos"] = photo_paths

        # 2) SRT 자막 파일 생성
        if script.subtitle_segments:
            srt_path = capcut_dir / "subtitles.srt"
            srt_lines = []
            for i, seg in enumerate(script.subtitle_segments, 1):
                start = self._seconds_to_srt(seg["start"])
                end = self._seconds_to_srt(seg["end"])
                srt_lines.append(f"{i}")
                srt_lines.append(f"{start} --> {end}")
                srt_lines.append(seg["text"])
                srt_lines.append("")
            srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
            result["srt"] = str(srt_path)

        # 3) 나레이션 음성 생성
        if script.narration_text:
            narr_path = await generate_tts(
                text=script.narration_text,
                output_path=capcut_dir / "narration.mp3",
                provider=tts_provider,
            )
            result["narration"] = str(narr_path)

        # 4) BGM 복사
        if bgm_path:
            from pathlib import Path
            bgm_src = Path(bgm_path)
            if bgm_src.exists():
                bgm_dst = capcut_dir / f"bgm{bgm_src.suffix}"
                shutil.copy2(str(bgm_src), str(bgm_dst))
                result["bgm"] = str(bgm_dst)

        # 5) CapCut 가이드 생성
        image_count = len(script.source_images)
        duration_per = min(8.0, 60.0 / image_count)

        guide = f"""CapCut 편집 가이드
==================

제목: {script.title}

1. CapCut을 열고 새 프로젝트를 만드세요 (비율: 4:5)

2. photos/ 폴더의 사진을 순서대로 타임라인에 추가하세요
   - 사진 {len(photo_paths)}장
   - 사진당 {duration_per:.1f}초

3. subtitles.srt 파일을 자막으로 가져오세요
   - CapCut > 텍스트 > 자막 가져오기 > subtitles.srt 선택
   - 오타 수정이 필요하면 자막을 클릭해서 직접 편집

4. narration.mp3 파일을 오디오 트랙에 추가하세요
   - 음성이 마음에 안 들면 직접 녹음해서 교체 가능

5. bgm 파일을 두 번째 오디오 트랙에 추가하세요
   - BGM 볼륨을 낮춰주세요 (나레이션의 20~30% 정도)

6. 내보내기: 1080x1350 / 30fps / MP4

자막 타임라인:
"""
        for seg in script.subtitle_segments:
            guide += f"  [{seg['start']:.0f}~{seg['end']:.0f}초] {seg['text']}\n"

        if script.narration_text:
            guide += f"\n나레이션 전문:\n{script.narration_text}\n"

        guide_path = capcut_dir / "guide.txt"
        guide_path.write_text(guide, encoding="utf-8")
        result["guide"] = str(guide_path)

        return result

    @staticmethod
    def _seconds_to_srt(seconds: float) -> str:
        """초를 SRT 타임스탬프로 변환 (00:00:05,000)."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    async def _generate_text(
        self,
        image_count: int,
        topic: str,
        mode: str,
        duration_per_image: float,
        total_duration: float,
    ) -> dict:
        """LLM으로 자막과 나레이션 텍스트를 생성한다."""
        prompt = SHORTS_SUBTITLE_USER.format(
            shop_context=self.shop.to_context_string(),
            image_count=image_count,
            mode="슬라이드쇼 + BGM" if mode == "slideshow" else "나레이션",
            topic=topic,
            duration_per_image=f"{duration_per_image:.1f}",
            total_duration=f"{total_duration:.0f}",
        )

        response = await self.llm.generate(
            prompt=prompt,
            provider=LLMProvider.CLAUDE,
            system=SHORTS_SUBTITLE_SYSTEM,
            max_tokens=2048,
            temperature=0.7,
        )

        try:
            text = response
            if "```" in text:
                text = text.replace("```json", "").replace("```", "")
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

        # 파싱 실패 시 기본 자막
        return {
            "title": topic,
            "description": "",
            "tags": [],
            "segments": [
                {"start": i * duration_per_image, "end": (i + 1) * duration_per_image, "text": f"사진 {i + 1}"}
                for i in range(image_count)
            ],
            "narration": topic,
        }
