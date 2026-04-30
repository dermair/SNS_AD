"""미디어 유틸리티 — 이미지 처리, TTS, FFmpeg 확인."""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

from src.core.config import OUTPUT_DIR

SHORTS_SIZE = (1080, 1350)  # 4:5 세로형 (인스타그램 최적)


def check_ffmpeg() -> bool:
    """FFmpeg 설치 여부를 확인한다."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def collect_images(path: str) -> list[Path]:
    """경로에서 이미지 파일들을 수집한다. 폴더면 내부 이미지, 파일이면 그 파일."""
    p = Path(path)
    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

    if p.is_dir():
        images = [f for f in sorted(p.iterdir()) if f.suffix.lower() in exts]
    elif p.is_file() and p.suffix.lower() in exts:
        images = [p]
    else:
        images = []

    return images


def resize_for_shorts(image_path: str | Path, output_path: str | Path | None = None) -> Path:
    """이미지를 9:16 세로형(1080x1920)으로 리사이즈한다.

    이미지 비율을 유지하면서 검은 배경 위에 중앙 배치.
    """
    img = Image.open(image_path).convert("RGB")
    target_w, target_h = SHORTS_SIZE

    # 비율 유지 리사이즈
    img_ratio = img.width / img.height
    target_ratio = target_w / target_h

    if img_ratio > target_ratio:
        # 이미지가 더 넓음 → 너비 기준
        new_w = target_w
        new_h = int(target_w / img_ratio)
    else:
        # 이미지가 더 높음 → 높이 기준
        new_h = target_h
        new_w = int(target_h * img_ratio)

    img_resized = img.resize((new_w, new_h), Image.LANCZOS)

    # 검은 배경에 중앙 배치
    canvas = Image.new("RGB", SHORTS_SIZE, (0, 0, 0))
    x = (target_w - new_w) // 2
    y = (target_h - new_h) // 2
    canvas.paste(img_resized, (x, y))

    out = Path(output_path) if output_path else Path(tempfile.mktemp(suffix=".jpg"))
    canvas.save(out, quality=95)
    return out


def create_before_after(
    before_path: str | Path,
    after_path: str | Path,
    output_path: str | Path | None = None,
) -> Path:
    """전후 비교 이미지를 좌우로 합성한다 (9:16)."""
    before = Image.open(before_path).convert("RGB")
    after = Image.open(after_path).convert("RGB")

    target_w, target_h = SHORTS_SIZE
    half_w = target_w // 2

    # 각 이미지를 절반 너비에 맞춤
    before_resized = before.resize((half_w, target_h), Image.LANCZOS)
    after_resized = after.resize((half_w, target_h), Image.LANCZOS)

    canvas = Image.new("RGB", SHORTS_SIZE, (0, 0, 0))
    canvas.paste(before_resized, (0, 0))
    canvas.paste(after_resized, (half_w, 0))

    out = Path(output_path) if output_path else Path(tempfile.mktemp(suffix=".jpg"))
    canvas.save(out, quality=95)
    return out


async def generate_tts(
    text: str,
    output_path: str | Path | None = None,
    voice: str = "ko-KR-SunHiNeural",
    provider: str = "edge-tts",
) -> Path:
    """TTS 음성을 생성한다.

    Args:
        text: 나레이션 텍스트
        output_path: 저장 경로
        voice: 음성 종류 (edge-tts: ko-KR-SunHiNeural 여성, ko-KR-InJoonNeural 남성)
        provider: "edge-tts" 또는 "openai"
    """
    out = Path(output_path) if output_path else Path(tempfile.mktemp(suffix=".mp3"))

    if provider == "edge-tts":
        import edge_tts

        communicate = edge_tts.Communicate(text=text, voice=voice)
        await communicate.save(str(out))
    elif provider == "openai":
        from openai import AsyncOpenAI
        from src.core.config import APIKeys

        keys = APIKeys.from_env()
        client = AsyncOpenAI(api_key=keys.openai)
        response = await client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text,
        )
        out.write_bytes(response.content)

    return out
