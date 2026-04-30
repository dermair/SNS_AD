# Architecture

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────┐
│                    CLI (main.py)                │
│         generate | review | list | setup        │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│              Orchestrator Agent                  │
│         (요청 분석 → 작업 분배 → 결과 통합)       │
│                  Claude API                      │
└──┬──────────────────┬───────────────────┬───────┘
   │                  │                   │
┌──▼─────┐    ┌──────▼──────┐    ┌───────▼──────┐
│ Blog   │    │ Instagram   │    │  YouTube     │
│ Agent  │    │ Agent       │    │  Agent       │
│Claude/ │    │ GPT+Gemini  │    │ Claude+Kling │
│  GPT   │    │             │    │              │
└──┬─────┘    └──────┬──────┘    └───────┬──────┘
   │                 │                   │
┌──▼─────┐    ┌──────▼──────┐    ┌───────▼──────┐
│ Blog   │    │ Instagram   │    │  YouTube     │
│Formatter│   │ Formatter   │    │  Formatter   │
└──┬─────┘    └──────┬──────┘    └───────┬──────┘
   │                 │                   │
   └────────┬────────┴───────────────────┘
            │
   ┌────────▼────────┐
   │  output/ 폴더   │
   │ (검수 → 업로드)  │
   └─────────────────┘
```

## 디렉토리 구조

```
src/
├── main.py              # CLI 엔트리포인트
├── agents/              # 에이전트 레이어 (비즈니스 로직)
├── core/                # 핵심 인프라 (API 클라이언트, 설정)
├── models/              # 데이터 모델 (dataclass)
├── platforms/           # 플랫폼별 포맷터
└── utils/               # 유틸리티 (해시태그, SEO)
```

## 레이어 설계

### Core Layer (`src/core/`)
- `config.py` — 환경변수, YAML 설정 로딩
- `llm.py` — Claude API + OpenAI GPT 통합 클라이언트
- `image_gen.py` — Gemini 2.5 이미지 생성
- `video_gen.py` — Kling AI 영상 생성
- `prompts.py` — 프롬프트 템플릿 관리

### Agent Layer (`src/agents/`)
- 각 에이전트는 `generate()` 메서드를 가진 클래스
- 오케스트레이터가 `asyncio.gather()`로 병렬 호출
- 에이전트는 Core Layer의 API 클라이언트를 사용

### Platform Layer (`src/platforms/`)
- 에이전트 출력을 플랫폼 규격에 맞게 포맷팅
- 블로그: 마크다운/HTML, 네이버 SEO 메타
- 인스타: 캡션 + 해시태그 + 이미지 프롬프트
- 유튜브: 스크립트 + 메타데이터 + 영상 프롬프트

### Model Layer (`src/models/`)
- `ShopProfile` — 피부관리실 기본 정보
- `ContentRequest` — 콘텐츠 생성 요청
- `ContentResult` — 생성된 콘텐츠 결과
- `PlatformContent` — 플랫폼별 콘텐츠

## 데이터 흐름

1. CLI → `ContentRequest` 생성
2. Orchestrator → 요청 분석 → 플랫폼별 지시사항 생성
3. 각 Agent → `PlatformContent` 생성 (텍스트 + 미디어)
4. Formatter → 플랫폼 규격에 맞게 변환
5. `ContentResult` → output/ 폴더에 저장
