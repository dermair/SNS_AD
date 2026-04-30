"""피부관리실 홍보 에이전트 CLI 엔트리포인트."""

from __future__ import annotations

import argparse
import asyncio
import io
import sys
from pathlib import Path

# Windows 콘솔 UTF-8 출력 설정
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

from src.core.config import APIKeys, ShopProfile, OUTPUT_DIR
from src.models.content import ContentRequest, ContentResult, Platform, ShortsContent
from src.agents.orchestrator import Orchestrator
from src.platforms.blog import BlogFormatter
from src.platforms.instagram import InstagramFormatter
from src.platforms.youtube import YouTubeFormatter

console = Console(force_terminal=True)


def print_banner():
    console.print(Panel.fit(
        "[bold magenta]피부관리실 홍보 에이전트[/bold magenta]\n"
        "블로그 · 인스타그램 · 유튜브 콘텐츠 자동 생성",
        border_style="magenta",
    ))


def cmd_setup():
    """샵 프로필 설정 확인."""
    console.print("\n[bold]샵 프로필 확인[/bold]\n")
    try:
        shop = ShopProfile.from_yaml()
        console.print(f"  샵 이름: [cyan]{shop.name}[/cyan]")
        console.print(f"  위치: {shop.location}")
        console.print(f"  시술 메뉴: {len(shop.services)}개")
        for s in shop.services:
            console.print(f"    - {s.name} ({s.price_range})")
        console.print(f"  프로모션: {len(shop.promotions)}개")
        console.print(f"\n  [green]프로필이 정상적으로 로드되었습니다.[/green]")
    except FileNotFoundError:
        console.print("  [red]config/shop_profile.yaml 파일을 찾을 수 없습니다.[/red]")
        console.print("  config/shop_profile.yaml 을 작성한 후 다시 시도하세요.")

    console.print("\n[bold]API 키 확인[/bold]\n")
    keys = APIKeys.from_env()
    missing = keys.validate()
    if missing:
        console.print(f"  [yellow]누락된 API 키:[/yellow] {', '.join(missing)}")
        console.print("  .env 파일에 API 키를 설정하세요.")
    else:
        console.print("  [green]모든 API 키가 설정되었습니다.[/green]")


async def cmd_generate(topic: str, platforms: list[str] | None, include_video: bool, guidelines_file: str | None = None):
    """콘텐츠를 생성한다."""
    console.print(f"\n[bold]콘텐츠 생성 시작[/bold]")
    console.print(f"  주제: [cyan]{topic}[/cyan]")

    # input/blog/info.yaml 자동 감지
    from src.utils.blog_input import load_blog_info
    blog_info = load_blog_info()
    if blog_info:
        console.print(f"  블로그 입력: [cyan]input/blog/info.yaml 감지됨[/cyan]")
        customers = blog_info.get("customers", [])
        console.print(f"    고객 케이스: {len(customers)}명")
        for c in customers:
            console.print(f"      - {c.get('name', '')} ({c.get('concern', '')})")

    # 설정 로드
    shop = ShopProfile.from_yaml()
    api_keys = APIKeys.from_env()

    missing = api_keys.validate()
    if missing:
        console.print(f"\n[red]누락된 API 키가 있습니다: {', '.join(missing)}[/red]")
        console.print(".env 파일을 확인하세요.")
        return

    # 플랫폼 결정
    if platforms:
        target_platforms = [Platform(p) for p in platforms]
    else:
        target_platforms = list(Platform)

    platform_names = ", ".join(p.value for p in target_platforms)
    console.print(f"  플랫폼: [cyan]{platform_names}[/cyan]")

    # CLI 지침 파일 로드
    guidelines_text = ""
    if guidelines_file:
        gpath = Path(guidelines_file)
        if gpath.exists():
            guidelines_text = gpath.read_text(encoding="utf-8").strip()
            console.print(f"  지침 파일: [cyan]{guidelines_file}[/cyan]")
        else:
            console.print(f"  [yellow]지침 파일을 찾을 수 없습니다: {guidelines_file}[/yellow]")

    # 요청 생성
    request = ContentRequest(
        topic=topic,
        platforms=target_platforms,
        include_video=include_video,
        blog_guidelines_override=guidelines_text,
    )

    # 오케스트레이터 실행
    orchestrator = Orchestrator(shop, api_keys)

    with console.status("[bold green]콘텐츠 생성 중...[/bold green]"):
        result = await orchestrator.generate(request)

    # 결과 저장 및 표시
    _display_and_save(result)


def _display_and_save(result: ContentResult):
    """결과를 터미널에 표시하고 파일로 저장."""
    saved_files: list[str] = []

    # 블로그
    blog = result.get_blog()
    if blog:
        console.print("\n" + "=" * 60)
        console.print("[bold blue]📝 블로그[/bold blue]\n")
        console.print(f"[bold]{blog.title}[/bold]")
        console.print(Markdown(blog.body[:500] + "..." if len(blog.body) > 500 else blog.body))
        console.print(f"\n태그: {', '.join(blog.tags[:10])}")

        formatter = BlogFormatter()
        path = formatter.save(blog)
        saved_files.append(path)

    # 인스타그램
    insta = result.get_instagram()
    if insta:
        console.print("\n" + "=" * 60)
        console.print("[bold purple]📸 인스타그램[/bold purple]\n")
        console.print(insta.caption[:300] + "..." if len(insta.caption) > 300 else insta.caption)
        console.print(f"\n해시태그 ({len(insta.hashtags)}개): {' '.join('#' + t for t in insta.hashtags[:10])} ...")

        formatter = InstagramFormatter()
        path = formatter.save(insta)
        saved_files.append(path)

    # 유튜브
    youtube = result.get_youtube()
    if youtube:
        console.print("\n" + "=" * 60)
        console.print("[bold red]🎬 유튜브[/bold red]\n")
        console.print(f"[bold]{youtube.title}[/bold]")
        console.print(f"유형: {youtube.duration_type}")
        console.print(youtube.script[:300] + "..." if len(youtube.script) > 300 else youtube.script)

        formatter = YouTubeFormatter()
        path = formatter.save(youtube)
        saved_files.append(path)

    # 저장 결과 요약
    if saved_files:
        console.print("\n" + "=" * 60)
        console.print("[bold green]저장 완료[/bold green]\n")
        for f in saved_files:
            console.print(f"  📄 {f}")
        console.print(f"\n[dim]output/ 폴더에서 전체 콘텐츠를 확인하세요.[/dim]")


def cmd_list():
    """생성된 콘텐츠 목록을 표시."""
    console.print("\n[bold]생성된 콘텐츠 목록[/bold]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("플랫폼", style="cyan")
    table.add_column("파일명")
    table.add_column("크기")
    table.add_column("생성일")

    for platform in ["blog", "instagram", "youtube"]:
        platform_dir = OUTPUT_DIR / platform
        if not platform_dir.exists():
            continue
        for f in sorted(platform_dir.glob("*.md"), reverse=True):
            stat = f.stat()
            size = f"{stat.st_size / 1024:.1f}KB"
            from datetime import datetime
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            table.add_row(platform, f.name, size, mtime)

    console.print(table)


def cmd_review():
    """최근 생성된 콘텐츠를 검수 모드로 표시."""
    console.print("\n[bold]콘텐츠 검수[/bold]\n")

    for platform in ["blog", "instagram", "youtube"]:
        platform_dir = OUTPUT_DIR / platform
        if not platform_dir.exists():
            continue

        files = sorted(platform_dir.glob("*.md"), reverse=True)
        if not files:
            continue

        latest = files[0]
        console.print(Panel(
            latest.read_text(encoding="utf-8")[:1000],
            title=f"[bold]{platform.upper()}[/bold] — {latest.name}",
            border_style="cyan",
        ))


async def cmd_shorts(images_path: str, topic: str, mode: str, bgm: str | None, tts: str, capcut: bool = False):
    """사진으로 쇼츠/릴스 영상을 자동 생성한다."""
    from src.utils.media import check_ffmpeg, collect_images
    from src.core.video_editor import VideoEditor
    from src.core.llm import LLMClient
    from src.agents.shorts_agent import ShortsAgent

    console.print(f"\n[bold]쇼츠/릴스 영상 생성[/bold]")

    # FFmpeg 확인
    if not check_ffmpeg():
        console.print("[red]FFmpeg가 설치되어 있지 않습니다.[/red]")
        console.print("설치: choco install ffmpeg 또는 winget install ffmpeg")
        return

    # 이미지 수집
    image_paths = collect_images(images_path)
    if not image_paths:
        console.print(f"[red]이미지를 찾을 수 없습니다: {images_path}[/red]")
        return

    console.print(f"  사진: [cyan]{len(image_paths)}장[/cyan]")
    console.print(f"  모드: [cyan]{mode}[/cyan]")
    if topic:
        console.print(f"  주제: [cyan]{topic}[/cyan]")

    # 설정 로드
    shop = ShopProfile.from_yaml()
    api_keys = APIKeys.from_env()

    if not api_keys.anthropic:
        console.print("[red]ANTHROPIC_API_KEY가 필요합니다.[/red]")
        return

    # 에이전트 실행
    llm = LLMClient(api_keys)
    editor = VideoEditor()
    agent = ShortsAgent(llm, shop, editor)

    # ── 1단계: 스크립트 생성 ──
    with console.status("[bold green]스크립트 생성 중...[/bold green]"):
        script = await agent.generate_script(
            image_paths=image_paths,
            topic=topic or shop.name,
            mode=mode,
        )

    # ── 스크립트 미리보기 ──
    console.print("\n" + "=" * 60)
    console.print("[bold cyan]스크립트 미리보기[/bold cyan]\n")
    if script.title:
        console.print(f"  제목: {script.title}")
    if script.description:
        console.print(f"  설명: {script.description}")
    if script.tags:
        console.print(f"  태그: {', '.join(script.tags[:10])}")
    console.print(f"  사진: {len(script.source_images)}장 / 모드: {script.mode}")

    if script.subtitle_segments:
        console.print("\n  [bold]자막 타임라인:[/bold]")
        for seg in script.subtitle_segments:
            console.print(f"    [{seg['start']:.0f}~{seg['end']:.0f}초] {seg['text']}")

    if script.narration_text:
        console.print(f"\n  [bold]나레이션:[/bold]")
        console.print(f"    {script.narration_text[:300]}{'...' if len(script.narration_text) > 300 else ''}")

    console.print("\n" + "=" * 60)

    # ── 사용자 확인 ──
    if capcut:
        confirm = input("\nCapCut 편집용 소스를 내보낼까요? (y/n): ").strip().lower()
    else:
        confirm = input("\n이 스크립트로 영상을 생성할까요? (y/n): ").strip().lower()
    if confirm not in ("y", "yes", "ㅛ"):
        console.print("[yellow]취소되었습니다.[/yellow]")
        return

    if capcut:
        # ── CapCut 소스 내보내기 ──
        with console.status("[bold green]CapCut 소스 내보내기 중...[/bold green]"):
            export = await agent.export_for_capcut(
                script=script,
                bgm_path=bgm,
                tts_provider=tts,
            )

        console.print("\n" + "=" * 60)
        console.print("[bold green]CapCut 소스 내보내기 완료[/bold green]\n")
        console.print(f"  폴더: [cyan]{export['capcut_dir']}[/cyan]")
        console.print(f"  사진: {len(export.get('photos', []))}장 (4:5 리사이즈)")
        if export.get("srt"):
            console.print(f"  자막: subtitles.srt (오타 수정 가능)")
        if export.get("narration"):
            console.print(f"  나레이션: narration.mp3 (교체 가능)")
        if export.get("bgm"):
            console.print(f"  BGM: bgm 파일 포함")
        console.print(f"  가이드: guide.txt")
        console.print(f"\n  [dim]CapCut에서 위 폴더를 열어 소스를 가져오세요.[/dim]")
    else:
        # ── 완성 영상 생성 ──
        with console.status("[bold green]영상 생성 중...[/bold green]"):
            result = await agent.generate_video(
                script=script,
                bgm_path=bgm,
                tts_provider=tts,
            )

        console.print("\n" + "=" * 60)
        console.print("[bold green]영상 생성 완료[/bold green]\n")
        if result.title:
            console.print(f"제목: {result.title}")
        if result.video_path:
            console.print(f"영상 파일: [green]{result.video_path}[/green]")
        console.print(f"사용 사진: {len(result.source_images)}장 / 모드: {result.mode}")


async def cmd_upload(platform: str, file_path: str | None, public: bool):
    """콘텐츠를 플랫폼에 업로드한다."""

    if platform == "youtube":
        await _upload_youtube(file_path, public)
    elif platform == "instagram":
        await _upload_instagram(file_path)
    elif platform == "blog":
        await _upload_naver_blog()


async def _upload_youtube(file_path: str | None, public: bool):
    """YouTube에 영상을 업로드한다."""
    from src.uploaders.youtube_uploader import YouTubeUploader

    console.print("\n[bold]YouTube 업로드[/bold]\n")

    # 영상 파일 결정
    if file_path:
        video_file = Path(file_path)
    else:
        # 최근 생성된 영상 자동 선택
        video_dir = OUTPUT_DIR / "youtube" / "videos"
        if not video_dir.exists():
            console.print("[red]영상 파일이 없습니다.[/red]")
            return
        videos = sorted(video_dir.glob("*.mp4"), reverse=True)
        if not videos:
            console.print("[red]영상 파일이 없습니다.[/red]")
            return
        video_file = videos[0]

    if not video_file.exists():
        console.print(f"[red]파일을 찾을 수 없습니다: {video_file}[/red]")
        return

    console.print(f"  파일: [cyan]{video_file.name}[/cyan]")
    console.print(f"  크기: {video_file.stat().st_size / 1024 / 1024:.1f}MB")

    # 메타데이터 찾기 (같은 타임스탬프의 .md 파일)
    title = video_file.stem
    description = ""
    tags = []

    # 최근 youtube_*.md 에서 메타데이터 추출
    meta_dir = OUTPUT_DIR / "youtube"
    meta_files = sorted(meta_dir.glob("youtube_*.md"), reverse=True)
    if meta_files:
        meta_text = meta_files[0].read_text(encoding="utf-8")
        for line in meta_text.splitlines():
            if line.startswith("## 제목"):
                # 다음 줄이 제목
                idx = meta_text.splitlines().index(line)
                if idx + 1 < len(meta_text.splitlines()):
                    title = meta_text.splitlines()[idx + 1].strip()
            elif line.startswith("## 태그"):
                idx = meta_text.splitlines().index(line)
                if idx + 1 < len(meta_text.splitlines()):
                    tags = [t.strip() for t in meta_text.splitlines()[idx + 1].split(",")]
            elif line.startswith("## 설명"):
                idx = meta_text.splitlines().index(line)
                desc_lines = []
                for dl in meta_text.splitlines()[idx + 1:]:
                    if dl.startswith("## "):
                        break
                    desc_lines.append(dl)
                description = "\n".join(desc_lines).strip()

    privacy = "public" if public else "private"

    # 미리보기
    console.print(f"\n  제목: [bold]{title}[/bold]")
    if tags:
        console.print(f"  태그: {', '.join(tags[:8])}")
    console.print(f"  공개: {'공개' if public else '비공개'}")

    console.print("")
    confirm = input("YouTube에 업로드할까요? (y/n): ").strip().lower()
    if confirm not in ("y", "yes", "ㅛ"):
        console.print("[yellow]취소되었습니다.[/yellow]")
        return

    # 인증
    uploader = YouTubeUploader()
    if not uploader.authenticate():
        return

    # 업로드
    console.print("")
    with console.status("[bold green]YouTube에 업로드 중...[/bold green]"):
        result = await uploader.upload_video(
            video_path=str(video_file),
            title=title,
            description=description,
            tags=tags,
            privacy=privacy,
            is_shorts=True,
        )

    console.print("\n[bold green]업로드 완료![/bold green]")
    console.print(f"  URL: [cyan]{result['url']}[/cyan]")
    console.print(f"  상태: {result['privacy']}")
    if result['privacy'] == 'private':
        console.print(f"  [dim]YouTube Studio에서 공개로 전환할 수 있습니다.[/dim]")


async def _upload_naver_blog():
    """네이버 블로그에 글을 업로드한다."""
    from src.uploaders.naver_blog_uploader import NaverBlogUploader

    console.print("\n[bold]네이버 블로그 업로드[/bold]\n")

    api_keys = APIKeys.from_env()
    uploader = NaverBlogUploader(api_keys)

    if not uploader.is_configured():
        console.print("[red]네이버 API가 설정되지 않았습니다.[/red]")
        console.print("  .env 파일에 다음을 설정하세요:")
        console.print("    NAVER_CLIENT_ID=클라이언트ID")
        console.print("    NAVER_CLIENT_SECRET=클라이언트시크릿")
        console.print("")
        console.print("  발급 방법:")
        console.print("  1. https://developers.naver.com 접속")
        console.print("  2. 애플리케이션 등록 → 블로그 API 선택")
        console.print("  3. Client ID / Client Secret 복사")
        return

    # 최근 블로그 글 찾기
    blog_dir = OUTPUT_DIR / "blog"
    blog_files = sorted(blog_dir.glob("blog_*.md"), reverse=True) if blog_dir.exists() else []
    if not blog_files:
        console.print("[red]블로그 글이 없습니다. 먼저 generate를 실행하세요.[/red]")
        return

    blog_text = blog_files[0].read_text(encoding="utf-8")

    # 제목과 본문 추출
    title = ""
    body_lines = []
    in_body = False
    for line in blog_text.splitlines():
        if line.startswith("# ") and not title:
            title = line[2:].strip()
            in_body = True
            continue
        if in_body and not line.startswith("---"):
            body_lines.append(line)

    body = "\n".join(body_lines).strip()

    # 태그 추출
    tags = []
    for line in blog_text.splitlines():
        if line.startswith("#") and not line.startswith("# "):
            tags = [t.strip().lstrip("#") for t in line.split() if t.startswith("#")]
            break

    console.print(f"  파일: [cyan]{blog_files[0].name}[/cyan]")
    console.print(f"  제목: [bold]{title}[/bold]")
    console.print(f"  본문: {len(body)}자")
    if tags:
        console.print(f"  태그: {', '.join(tags[:8])}")
    console.print("")

    confirm = input("네이버 블로그에 업로드할까요? (y/n): ").strip().lower()
    if confirm not in ("y", "yes", "ㅛ"):
        console.print("[yellow]취소되었습니다.[/yellow]")
        return

    # 인증
    if not uploader.authenticate():
        console.print("[red]네이버 인증에 실패했습니다.[/red]")
        return

    try:
        with console.status("[bold green]네이버 블로그에 업로드 중...[/bold green]"):
            result = await uploader.upload_post(
                title=title,
                content=body,
                tags=tags,
            )

        console.print("\n[bold green]업로드 완료![/bold green]")
        if result.get("blog_url"):
            console.print(f"  URL: [cyan]{result['blog_url']}/{result.get('log_no', '')}[/cyan]")
    except Exception as e:
        console.print(f"\n[red]업로드 실패: {e}[/red]")
    finally:
        await uploader.close()


async def _upload_instagram(file_path: str | None):
    """Instagram에 콘텐츠를 업로드한다."""
    from src.uploaders.instagram_uploader import InstagramUploader

    console.print("\n[bold]Instagram 업로드[/bold]\n")

    api_keys = APIKeys.from_env()
    uploader = InstagramUploader(api_keys)

    if not uploader.is_configured():
        console.print("[red]Instagram API가 설정되지 않았습니다.[/red]")
        console.print("  .env 파일에 다음을 설정하세요:")
        console.print("    INSTAGRAM_ACCESS_TOKEN=토큰값")
        console.print("    INSTAGRAM_USER_ID=사용자ID")
        console.print("")
        console.print("  발급 방법:")
        console.print("  1. Instagram을 Business/Creator 계정으로 전환")
        console.print("  2. Facebook Page와 연결")
        console.print("  3. Meta for Developers에서 앱 등록")
        console.print("  4. instagram_business_content_publish 권한 요청")
        return

    # 캡션 파일 찾기
    caption_dir = OUTPUT_DIR / "instagram"
    caption_files = sorted(caption_dir.glob("caption_*.txt"), reverse=True)
    if not caption_files:
        console.print("[red]Instagram 캡션 파일이 없습니다. 먼저 generate를 실행하세요.[/red]")
        return

    caption = caption_files[0].read_text(encoding="utf-8")

    # 이미지 또는 영상 결정
    if file_path:
        media_file = Path(file_path)
    else:
        # 최근 이미지 또는 영상 찾기
        image_dir = OUTPUT_DIR / "instagram" / "images"
        video_dir = OUTPUT_DIR / "youtube" / "videos"

        images = sorted(image_dir.glob("*.png"), reverse=True) if image_dir.exists() else []
        videos = sorted(video_dir.glob("*.mp4"), reverse=True) if video_dir.exists() else []

        if images:
            media_file = images[0]
        elif videos:
            media_file = videos[0]
        else:
            console.print("[red]업로드할 이미지/영상이 없습니다.[/red]")
            return

    console.print(f"  파일: [cyan]{media_file.name}[/cyan]")
    console.print(f"  캡션: {caption[:100]}...")
    console.print("")

    confirm = input("Instagram에 업로드할까요? (y/n): ").strip().lower()
    if confirm not in ("y", "yes", "ㅛ"):
        console.print("[yellow]취소되었습니다.[/yellow]")
        return

    console.print("")
    console.print("[yellow]Instagram Graph API는 공개 URL에서 미디어를 다운로드합니다.[/yellow]")
    console.print("[yellow]로컬 파일은 먼저 호스팅 서비스에 업로드해야 합니다.[/yellow]")
    media_url = input("미디어 공개 URL을 입력하세요 (또는 Enter로 취소): ").strip()
    if not media_url:
        console.print("[yellow]취소되었습니다.[/yellow]")
        return

    is_video = media_file.suffix.lower() == ".mp4"

    try:
        with console.status("[bold green]Instagram에 업로드 중...[/bold green]"):
            if is_video:
                result = await uploader.upload_reels(video_url=media_url, caption=caption)
            else:
                result = await uploader.upload_image(image_url=media_url, caption=caption)

        console.print("\n[bold green]업로드 완료![/bold green]")
        console.print(f"  Media ID: {result['media_id']}")
    except Exception as e:
        console.print(f"\n[red]업로드 실패: {e}[/red]")
    finally:
        await uploader.close()


async def cmd_morning():
    """아침 대화형 모드 — 텔레그램으로 질문 후 콘텐츠 생성."""
    from src.telegram_bot import TelegramBot

    console.print("\n[bold]아침 대화형 모드[/bold]\n")

    bot = TelegramBot()
    if not bot.notifier.is_configured():
        console.print("[red]텔레그램 봇이 설정되지 않았습니다.[/red]")
        return

    console.print("  텔레그램으로 질문을 보냅니다...")
    console.print("  답장을 기다립니다 (최대 2시간)...\n")

    await bot.run_morning()

    console.print("\n[green]완료![/green]")


async def cmd_telegram(platform: str):
    """최근 콘텐츠를 텔레그램으로 전송한다."""
    from src.notifier import TelegramNotifier

    console.print(f"\n[bold]텔레그램으로 콘텐츠 전송[/bold]\n")

    notifier = TelegramNotifier()
    if not notifier.is_configured():
        console.print("[red]KAKAO_CHANNEL_TOKEN이 설정되지 않았습니다.[/red]")
        return

    # 최근 파일 찾기
    if platform == "blog":
        files = sorted((OUTPUT_DIR / "blog").glob("blog_*.md"), reverse=True)
    elif platform == "instagram":
        files = sorted((OUTPUT_DIR / "instagram").glob("instagram_*.md"), reverse=True)
    elif platform == "youtube":
        files = sorted((OUTPUT_DIR / "youtube").glob("youtube_*.md"), reverse=True)
    else:
        files = []

    if not files:
        console.print(f"[red]{platform} 콘텐츠가 없습니다.[/red]")
        return

    latest = files[0]
    content = latest.read_text(encoding="utf-8")

    console.print(f"  파일: [cyan]{latest.name}[/cyan]")
    console.print(f"  크기: {len(content)}자")

    with console.status("[bold green]텔레그램 전송 중...[/bold green]"):
        sent = await notifier.send_content_preview(content, platform)

    if sent:
        console.print(f"\n[green]텔레그램 전송 완료![/green] 텔레그램을 확인하세요.")
    else:
        console.print(f"\n[red]전송 실패[/red]")

    await notifier.close()


async def cmd_schedule_auto(day: str | None):
    """자동 생성 + 텔레그램 결과 전송 (스케줄러용)."""
    from src.scheduler import Scheduler

    try:
        scheduler = Scheduler()
    except FileNotFoundError:
        console.print("[red]config/schedule.yaml 파일이 없습니다.[/red]")
        return

    task_info = scheduler.get_today_task(day)
    if task_info["task"] == "off":
        return

    day_kr = {"monday":"월","tuesday":"화","wednesday":"수","thursday":"목","friday":"금","saturday":"토","sunday":"일"}.get(task_info["day"], task_info["day"])
    task_kr = {"youtube_shorts":"유튜브 쇼츠","blog":"네이버 블로그","instagram_carousel":"인스타 캐러셀","instagram_reels":"인스타 릴스"}.get(task_info["task"], task_info["task"])

    console.print(f"\n[bold]{day_kr}요일 자동 실행: {task_kr}[/bold]\n")

    result = await scheduler.auto_run(day)

    status = result.get("status", "unknown")
    if status == "generated":
        console.print(f"[green]완료! 텔레그램으로 결과가 전송되었습니다.[/green]")
    else:
        console.print(f"결과: {status}")


async def cmd_schedule_notify(day: str | None):
    """오늘 할 작업을 카카오톡으로 알린다."""
    from src.scheduler import Scheduler

    console.print("\n[bold]카카오톡 알림 전송[/bold]\n")

    try:
        scheduler = Scheduler()
    except FileNotFoundError:
        console.print("[red]config/schedule.yaml 파일이 없습니다.[/red]")
        return

    result = await scheduler.notify(day)

    if result.get("status") == "skip":
        console.print("  오늘은 휴무일입니다.")
    elif result.get("status") == "notified":
        day_kr = {"monday":"월","tuesday":"화","wednesday":"수","thursday":"목","friday":"금","saturday":"토","sunday":"일"}.get(result["day"], result["day"])
        console.print(f"  [green]카카오톡 알림 전송 완료![/green]")
        console.print(f"  {day_kr}요일: {result['task']} / 주제: {result['topic']}")
        console.print(f"\n  승인하려면: python -m src.main schedule run")
    elif result.get("status") == "send_failed":
        console.print("[red]카카오톡 전송 실패.[/red]")
        console.print("  카카오 개발자 콘솔에서 현재 IP를 허용 IP로 등록하세요.")
        console.print(f"\n  오늘 작업: {result['task']} / 주제: {result['topic']}")
    elif result.get("status") == "not_configured":
        console.print("[yellow]텔레그램 봇이 설정되지 않았습니다.[/yellow]")
        console.print("  .env에 TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID를 설정하세요.")
        console.print(f"\n  오늘 작업: {result['task']} / 주제: {result['topic']}")


async def cmd_schedule_run(day: str | None):
    """스케줄 작업을 실행한다."""
    from src.scheduler import Scheduler

    console.print("\n[bold]스케줄 실행[/bold]\n")

    try:
        scheduler = Scheduler()
    except FileNotFoundError:
        console.print("[red]config/schedule.yaml 파일이 없습니다.[/red]")
        return

    task_info = scheduler.get_today_task(day)
    day_name = task_info["day"]
    task = task_info["task"]

    day_kr = {"monday":"월","tuesday":"화","wednesday":"수","thursday":"목","friday":"금","saturday":"토","sunday":"일"}.get(day_name, day_name)

    if task == "off":
        console.print(f"  {day_kr}요일: [dim]휴무일 — 건너뜁니다.[/dim]")
        return

    task_kr = {"youtube_shorts":"유튜브 쇼츠","blog":"네이버 블로그","instagram_carousel":"인스타 캐러셀","instagram_reels":"인스타 릴스"}.get(task, task)
    console.print(f"  {day_kr}요일: [cyan]{task_kr}[/cyan]")

    with console.status(f"[bold green]{task_kr} 생성 중...[/bold green]"):
        result = await scheduler.run(day)

    status = result.get("status", "unknown")
    if status == "generated":
        console.print(f"\n[bold green]완료![/bold green]")
        console.print(f"  주제: {result.get('topic', '')}")
        if result.get("file"):
            console.print(f"  파일: [cyan]{result['file']}[/cyan]")
    elif status == "no_topic":
        console.print(f"\n[yellow]주제가 없습니다. schedule add-topic으로 추가하세요.[/yellow]")
    elif status == "no_images":
        console.print(f"\n[yellow]input/ 폴더에 사진이 없습니다.[/yellow]")
    else:
        console.print(f"\n[red]실행 결과: {status}[/red]")


def cmd_schedule_status():
    """스케줄 상태를 표시한다."""
    from src.scheduler import Scheduler

    console.print("\n[bold]스케줄 상태[/bold]\n")

    try:
        scheduler = Scheduler()
    except FileNotFoundError:
        console.print("[red]config/schedule.yaml 파일이 없습니다.[/red]")
        return

    status = scheduler.get_status()
    today = status["today"]
    day_kr = {"monday":"월","tuesday":"화","wednesday":"수","thursday":"목","friday":"금","saturday":"토","sunday":"일"}.get(today["day"], today["day"])
    task_kr = {"youtube_shorts":"유튜브 쇼츠","blog":"네이버 블로그","instagram_carousel":"인스타 캐러셀","instagram_reels":"인스타 릴스","off":"휴무"}.get(today["task"], today["task"])

    console.print(f"  오늘 ({day_kr}요일): [cyan]{task_kr}[/cyan] — {today['time']}")
    console.print(f"  주제 큐: [cyan]{status['queue_count']}개[/cyan] 남음")
    if status["queue_preview"]:
        for t in status["queue_preview"]:
            console.print(f"    - {t}")
    console.print(f"  AI 자동 주제: {'켜짐' if status['auto_topic'] else '꺼짐'}")

    if status["recent_logs"]:
        console.print(f"\n  [bold]최근 실행 기록:[/bold]")
        for log in status["recent_logs"]:
            console.print(f"    {log}")

    # 주간 스케줄 요약
    console.print(f"\n  [bold]주간 스케줄:[/bold]")
    days = [("monday","월"),("tuesday","화"),("wednesday","수"),("thursday","목"),("friday","금"),("saturday","토"),("sunday","일")]
    for en, kr in days:
        task = scheduler.get_today_task(en)["task"]
        t_kr = {"youtube_shorts":"유튜브 쇼츠","blog":"네이버 블로그","instagram_carousel":"인스타 캐러셀","instagram_reels":"인스타 릴스","off":"휴무"}.get(task, task)
        marker = " ◀ 오늘" if en == today["day"] else ""
        console.print(f"    {kr}: {t_kr}{marker}")


def cmd_schedule_add_topic(topic: str):
    """주제 큐에 새 주제를 추가한다."""
    from src.scheduler import Scheduler

    try:
        scheduler = Scheduler()
    except FileNotFoundError:
        console.print("[red]config/schedule.yaml 파일이 없습니다.[/red]")
        return

    scheduler.add_topic(topic)
    queue = scheduler.config.get("topic_queue", [])
    console.print(f"\n[green]주제 추가 완료:[/green] {topic}")
    console.print(f"  큐 잔여: {len(queue)}개")


def main():
    print_banner()

    parser = argparse.ArgumentParser(description="피부관리실 홍보 콘텐츠 에이전트")
    subparsers = parser.add_subparsers(dest="command")

    # setup
    subparsers.add_parser("setup", help="샵 프로필 및 API 키 확인")

    # generate
    gen_parser = subparsers.add_parser("generate", help="콘텐츠 생성")
    gen_parser.add_argument("topic", help="콘텐츠 주제 (예: '젤네일 20%% 할인 이벤트')")
    gen_parser.add_argument(
        "--platform", "-p",
        choices=["blog", "instagram", "youtube"],
        action="append",
        help="특정 플랫폼만 생성 (여러 번 지정 가능)",
    )
    gen_parser.add_argument("--video", action="store_true", help="영상 생성 포함 (Kling AI)")
    gen_parser.add_argument("--guidelines", "-g", help="블로그 작성 지침 파일 경로 (YAML 기본 지침에 추가)")

    # shorts
    shorts_parser = subparsers.add_parser("shorts", help="사진으로 쇼츠/릴스 영상 자동 생성")
    shorts_parser.add_argument("--images", "-i", required=True, help="사진 폴더 경로 또는 파일 경로")
    shorts_parser.add_argument("--topic", "-t", default="", help="영상 주제 (예: '여드름 케어 전후')")
    shorts_parser.add_argument("--mode", "-m", choices=["slideshow", "narration"], default="slideshow", help="slideshow (BGM) 또는 narration (AI 음성)")
    shorts_parser.add_argument("--bgm", help="BGM 파일 경로 (slideshow 모드)")
    shorts_parser.add_argument("--tts", choices=["edge-tts", "openai"], default="edge-tts", help="TTS 제공자")
    shorts_parser.add_argument("--capcut", action="store_true", help="CapCut 편집용 소스 분리 내보내기")

    # upload
    upload_parser = subparsers.add_parser("upload", help="콘텐츠를 플랫폼에 업로드")
    upload_parser.add_argument("--platform", "-p", required=True, choices=["youtube", "instagram", "blog"], help="업로드 대상 플랫폼")
    upload_parser.add_argument("--file", "-f", help="업로드할 파일 경로 (미지정 시 최근 파일)")
    upload_parser.add_argument("--public", action="store_true", help="공개로 업로드 (기본: 비공개)")

    # schedule
    sched_parser = subparsers.add_parser("schedule", help="콘텐츠 스케줄 관리")
    sched_sub = sched_parser.add_subparsers(dest="schedule_action")
    sched_auto = sched_sub.add_parser("auto", help="자동 생성 + 카카오톡 결과 전송 (스케줄러용)")
    sched_auto.add_argument("--day", choices=["monday","tuesday","wednesday","thursday","friday","saturday","sunday"], help="특정 요일 지정")
    sched_notify = sched_sub.add_parser("notify", help="오늘 할 작업을 텔레그램으로 알림만")
    sched_notify.add_argument("--day", choices=["monday","tuesday","wednesday","thursday","friday","saturday","sunday"], help="특정 요일 지정")
    sched_run = sched_sub.add_parser("run", help="수동 스케줄 실행")
    sched_run.add_argument("--day", choices=["monday","tuesday","wednesday","thursday","friday","saturday","sunday"], help="특정 요일 지정 실행")
    sched_sub.add_parser("status", help="스케줄 상태 확인")
    sched_add = sched_sub.add_parser("add-topic", help="주제 큐에 추가")
    sched_add.add_argument("topic", help="추가할 주제")

    # list
    subparsers.add_parser("list", help="생성된 콘텐츠 목록")

    # review
    subparsers.add_parser("review", help="최근 콘텐츠 검수")

    # telegram
    tg_parser = subparsers.add_parser("telegram", help="최근 콘텐츠를 텔레그램으로 전송")
    tg_parser.add_argument("--platform", "-p", choices=["blog", "instagram", "youtube"], default="blog", help="전송할 플랫폼 콘텐츠")

    # morning (매일 아침 대화형 모드)
    subparsers.add_parser("morning", help="아침 대화형 모드 — 텔레그램으로 질문 → 답변 → 생성")

    args = parser.parse_args()

    if args.command == "setup":
        cmd_setup()
    elif args.command == "generate":
        asyncio.run(cmd_generate(args.topic, args.platform, args.video, args.guidelines))
    elif args.command == "shorts":
        asyncio.run(cmd_shorts(args.images, args.topic, args.mode, args.bgm, args.tts, getattr(args, 'capcut', False)))
    elif args.command == "upload":
        asyncio.run(cmd_upload(args.platform, args.file, args.public))
    elif args.command == "schedule":
        if args.schedule_action == "auto":
            asyncio.run(cmd_schedule_auto(getattr(args, 'day', None)))
        elif args.schedule_action == "notify":
            asyncio.run(cmd_schedule_notify(getattr(args, 'day', None)))
        elif args.schedule_action == "run":
            asyncio.run(cmd_schedule_run(args.day))
        elif args.schedule_action == "status":
            cmd_schedule_status()
        elif args.schedule_action == "add-topic":
            cmd_schedule_add_topic(args.topic)
        else:
            sched_parser.print_help()
    elif args.command == "telegram":
        asyncio.run(cmd_telegram(args.platform))
    elif args.command == "morning":
        asyncio.run(cmd_morning())
    elif args.command == "list":
        cmd_list()
    elif args.command == "review":
        cmd_review()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
