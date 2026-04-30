"""영상 편집 엔진 — 사진을 쇼츠/릴스 영상으로 자동 변환."""

from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np
from moviepy import (
    ImageClip,
    TextClip,
    CompositeVideoClip,
    AudioFileClip,
    concatenate_videoclips,
)

from src.core.config import OUTPUT_DIR
from src.utils.media import resize_for_shorts, SHORTS_SIZE


class VideoEditor:
    """사진 → 영상 자동 편집 엔진."""

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or OUTPUT_DIR / "youtube" / "videos"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def create_slideshow(
        self,
        image_paths: list[str | Path],
        duration_per_image: float = 4.0,
        max_duration: float = 60.0,
        transition: str = "fade",
    ) -> dict:
        """사진들을 슬라이드쇼 영상으로 합성한다.

        Args:
            image_paths: 사진 경로 리스트
            duration_per_image: 사진당 표시 시간 (초)
            max_duration: 최대 영상 길이 (초)
            transition: 전환 효과 ("fade" or "cut")

        Returns:
            {"path": 영상 경로, "duration": 총 길이}
        """
        if not image_paths:
            raise ValueError("이미지가 없습니다")

        # 총 시간이 max_duration을 넘지 않도록 조정
        total_images = len(image_paths)
        adjusted_duration = min(duration_per_image, max_duration / total_images)

        # 각 이미지를 9:16으로 리사이즈 후 클립 생성
        clips = []
        for img_path in image_paths:
            resized = resize_for_shorts(img_path)
            clip = ImageClip(str(resized)).with_duration(adjusted_duration)
            clips.append(clip)

        video = concatenate_videoclips(clips, method="compose")

        # 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"shorts_{timestamp}.mp4"

        await asyncio.to_thread(
            video.write_videofile,
            str(output_path),
            fps=30,
            codec="libx264",
            audio=False,
            logger=None,
        )

        video.close()
        return {"path": str(output_path), "duration": video.duration}

    def _render_subtitle_image(self, text: str, max_width: int = 980) -> np.ndarray:
        """Pillow로 한글 자막을 RGBA 이미지로 렌더링한다.

        받침 잘림 없이 정확하게 렌더링하며, 외곽선(stroke)으로 가독성 확보.
        """
        from PIL import Image, ImageDraw, ImageFont

        font = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 44)

        # 텍스트 줄바꿈 처리
        lines = []
        current_line = ""
        for char in text:
            test = current_line + char
            bbox = font.getbbox(test)
            if bbox[2] - bbox[0] > max_width:
                lines.append(current_line)
                current_line = char
            else:
                current_line = test
        if current_line:
            lines.append(current_line)

        # 이미지 크기 계산 (줄 높이에 넉넉한 여백)
        line_height = 60
        padding = 20
        img_w = SHORTS_SIZE[0]
        img_h = line_height * len(lines) + padding * 2

        img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 각 줄을 중앙 정렬로 렌더링 (외곽선 + 본문)
        for i, line in enumerate(lines):
            bbox = font.getbbox(line)
            text_w = bbox[2] - bbox[0]
            x = (img_w - text_w) // 2
            y = padding + i * line_height

            # 외곽선 (8방향)
            stroke = 4
            for dx in range(-stroke, stroke + 1):
                for dy in range(-stroke, stroke + 1):
                    if dx == 0 and dy == 0:
                        continue
                    draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, 255))

            # 본문 (흰색)
            draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))

        return np.array(img)

    async def add_subtitles(
        self,
        video_path: str | Path,
        subtitle_segments: list[dict],
    ) -> dict:
        """영상에 자막을 오버레이한다.

        Args:
            video_path: 원본 영상 경로
            subtitle_segments: [{"start": 0, "end": 3, "text": "자막 내용"}, ...]

        Returns:
            {"path": 자막 추가된 영상 경로}
        """
        from moviepy import VideoFileClip

        video = VideoFileClip(str(video_path))
        subtitle_clips = []

        # 인스타그램 세이프존: 자막을 영상 높이의 약 72% 지점에 배치
        subtitle_y = int(SHORTS_SIZE[1] * 0.72)

        for seg in subtitle_segments:
            # Pillow로 한글 자막 렌더링 (받침 잘림 없음)
            sub_img = self._render_subtitle_image(seg["text"])

            txt_clip = (
                ImageClip(sub_img, transparent=True)
                .with_position(("center", subtitle_y))
                .with_start(seg["start"])
                .with_duration(seg["end"] - seg["start"])
            )
            subtitle_clips.append(txt_clip)

        final = CompositeVideoClip([video] + subtitle_clips)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"shorts_sub_{timestamp}.mp4"

        await asyncio.to_thread(
            final.write_videofile,
            str(output_path),
            fps=30,
            codec="libx264",
            logger=None,
        )

        video.close()
        final.close()
        return {"path": str(output_path)}

    async def add_bgm(
        self,
        video_path: str | Path,
        bgm_path: str | Path,
        volume: float = 0.3,
    ) -> dict:
        """영상에 배경음악을 합성한다.

        Args:
            video_path: 원본 영상 경로
            bgm_path: BGM 파일 경로
            volume: BGM 볼륨 (0.0~1.0)
        """
        from moviepy import VideoFileClip

        video = VideoFileClip(str(video_path))
        bgm = AudioFileClip(str(bgm_path))

        # BGM을 영상 길이에 맞게 자르기
        if bgm.duration > video.duration:
            bgm = bgm.subclipped(0, video.duration)

        bgm = bgm.with_volume_scaled(volume)

        # 기존 오디오가 있으면 합성, 없으면 BGM만
        if video.audio:
            from moviepy import CompositeAudioClip
            mixed = CompositeAudioClip([video.audio, bgm])
            final = video.with_audio(mixed)
        else:
            final = video.with_audio(bgm)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"shorts_bgm_{timestamp}.mp4"

        await asyncio.to_thread(
            final.write_videofile,
            str(output_path),
            fps=30,
            codec="libx264",
            audio_codec="aac",
            logger=None,
        )

        video.close()
        final.close()
        return {"path": str(output_path)}

    async def add_narration(
        self,
        video_path: str | Path,
        narration_path: str | Path,
    ) -> dict:
        """영상에 나레이션 오디오를 합성한다."""
        from moviepy import VideoFileClip

        video = VideoFileClip(str(video_path))
        narration = AudioFileClip(str(narration_path))

        # 나레이션이 영상보다 길면 영상 연장 (마지막 프레임 유지)
        if narration.duration > video.duration:
            video = video.with_duration(narration.duration)

        final = video.with_audio(narration)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"shorts_narr_{timestamp}.mp4"

        await asyncio.to_thread(
            final.write_videofile,
            str(output_path),
            fps=30,
            codec="libx264",
            audio_codec="aac",
            logger=None,
        )

        video.close()
        final.close()
        return {"path": str(output_path)}
