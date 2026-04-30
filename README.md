# 피부관리실 홍보 에이전트

블로그, 인스타그램, 유튜브 콘텐츠를 자동으로 생성하고 업로드하는 AI 에이전트입니다.


## 1단계: 사전 준비

### Python 설치
- Python 3.11 이상 필요
- https://www.python.org/downloads/ 에서 다운로드
- 설치 시 "Add Python to PATH" 체크

### FFmpeg 설치 (영상 편집용)
- Windows: 관리자 권한 터미널에서
```
winget install ffmpeg
```
- 또는 https://ffmpeg.org/download.html 에서 다운로드 후 PATH 설정

### 설치 확인
```
python --version
ffmpeg -version
```


## 2단계: 프로젝트 설치

```bash
# 프로젝트 폴더로 이동
cd C:\Users\사용자이름\Desktop\ai2

# 패키지 설치
pip install -r requirements.txt
```


## 3단계: API 키 설정

`.env.example` 파일을 복사해서 `.env` 파일을 만드세요.

```bash
copy .env.example .env
```

`.env` 파일을 열어서 API 키를 입력하세요.

### 필수 API 키 (콘텐츠 생성용)

| API | 발급 방법 | .env 키 |
|-----|----------|---------|
| Claude | https://console.anthropic.com → API Keys | ANTHROPIC_API_KEY |
| OpenAI | https://platform.openai.com → API Keys | OPENAI_API_KEY |
| Gemini | https://aistudio.google.com/apikey | GOOGLE_API_KEY |

### 선택 API 키 (영상 생성/업로드용)

| API | 발급 방법 | .env 키 |
|-----|----------|---------|
| Kling AI | https://klingai.com → 개발자 플랫폼 | KLING_API_KEY, KLING_API_SECRET |
| 카카오톡 | 아래 카카오톡 설정 참고 | KAKAO_CHANNEL_TOKEN |
| Instagram | 아래 Instagram 설정 참고 | INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID |
| 네이버 | 아래 네이버 설정 참고 | NAVER_CLIENT_ID, NAVER_CLIENT_SECRET |
| YouTube | 아래 YouTube 설정 참고 | config/client_secrets.json 파일 |


## 4단계: 샵 프로필 설정

`config/shop_profile.example.yaml` 파일을 복사한 후 본인 매장 정보로 수정하세요.

```bash
copy config\shop_profile.example.yaml config\shop_profile.yaml
```

```yaml
shop:
  name: "내 매장 이름"
  description: "매장 한 줄 소개"
  location: "매장 주소"
  phone: "전화번호"
  instagram: "@인스타계정"
  blog: "블로그 주소"
  youtube: "@유튜브채널"

  services:
    - name: "시술명"
      price_range: "가격대"
      duration: "소요시간"
      keywords: ["키워드1", "키워드2"]

  tone:
    style: "톤앤매너"
    target_audience: "타겟 고객"
```


## 5단계: 설치 확인

```bash
python -m src.main setup
```

샵 정보와 API 키 상태가 표시됩니다.


## 사용법

### 콘텐츠 생성

```bash
# 블로그 + 인스타 + 유튜브 동시 생성
python -m src.main generate "여드름 관리 후기"

# 블로그만 생성
python -m src.main generate "여드름 관리 후기" -p blog

# 추가 지침 파일 적용
python -m src.main generate "여드름 관리 후기" -g my_style.txt
```

### 고객 정보로 블로그 글 생성

1. `input/blog/info.yaml` 에 고객 정보 입력
2. `input/blog/` 폴더에 사진 넣기 (before_1.jpg, after_1.jpg 등)
3. 실행:
```bash
python -m src.main generate "여드름 관리 후기" -p blog
```

### 영상 자동 편집

```bash
# 사진으로 슬라이드쇼 영상 (자막 포함)
python -m src.main shorts -i ./input/ -t "여드름 케어 전후"

# AI 나레이션 모드
python -m src.main shorts -i ./input/ -t "여드름 케어 전후" -m narration

# BGM 추가
python -m src.main shorts -i ./input/ --bgm music.mp3
```

### 업로드

```bash
python -m src.main upload -p youtube      # YouTube 업로드
python -m src.main upload -p instagram    # Instagram 업로드
python -m src.main upload -p blog         # 네이버 블로그 업로드
```

### 카카오톡으로 결과 확인

```bash
python -m src.main kakao -p blog          # 블로그 글
python -m src.main kakao -p instagram     # 인스타 콘텐츠
python -m src.main kakao -p youtube       # 유튜브 스크립트
```

### 스케줄 관리

```bash
python -m src.main schedule status        # 주간 스케줄 확인
python -m src.main schedule auto          # 오늘 작업 자동 실행 + 카카오 전송
python -m src.main schedule run           # 오늘 작업 수동 실행
python -m src.main schedule add-topic "주제"  # 주제 추가
```

### 콘텐츠 관리

```bash
python -m src.main list                   # 생성된 콘텐츠 목록
python -m src.main review                 # 최근 콘텐츠 미리보기
```


## 스케줄 자동화 (매일 09:00)

### 방법 1: bat 파일 실행
`config/schedule_register.bat` 를 관리자 권한으로 실행

### 방법 2: 직접 등록
관리자 권한 터미널에서:
```
schtasks /create /tn "BeautyAgentNotify" /tr "cmd /c cd /d C:\프로젝트경로 && python -m src.main schedule auto" /sc daily /st 09:00 /f
```

### 스케줄 삭제
```
schtasks /delete /tn "BeautyAgentNotify" /f
```

### 기본 주간 스케줄

| 요일 | 작업 |
|------|------|
| 월 | 유튜브 쇼츠 |
| 화 | 네이버 블로그 |
| 수 | 인스타 캐러셀 |
| 목 | 네이버 블로그 |
| 금 | 인스타 릴스 |
| 토 | 인스타 캐러셀 |
| 일 | 휴무 |

`config/schedule.yaml` 에서 요일별 작업과 주제 큐를 수정할 수 있습니다.


## 카카오톡 알림 설정

1. https://developers.kakao.com 접속 → 앱 등록
2. 앱 설정 → 카카오로그인 → 사용설정 ON
3. 카카오로그인 → 동의항목 → talk_message 설정
4. 카카오로그인 → 고급 → Client Secret 확인
5. 브라우저에서 인증:
```
https://kauth.kakao.com/oauth/authorize?client_id=REST_API키&redirect_uri=http://localhost:3000/callback&response_type=code&scope=talk_message
```
6. 리다이렉트된 URL에서 code= 값 복사
7. 토큰 교환:
```bash
python -c "
import requests
resp = requests.post('https://kauth.kakao.com/oauth/token', data={
    'grant_type': 'authorization_code',
    'client_id': 'REST_API키',
    'client_secret': 'Client_Secret',
    'redirect_uri': 'http://localhost:3000/callback',
    'code': '복사한코드',
})
print(resp.json().get('access_token'))
"
```
8. `.env`에 `KAKAO_CHANNEL_TOKEN=발급받은토큰` 입력


## YouTube 업로드 설정

1. https://console.cloud.google.com 접속
2. 프로젝트 생성 → YouTube Data API v3 활성화
3. 사용자 인증 정보 → OAuth 2.0 클라이언트 ID 생성 (데스크톱 앱)
4. JSON 다운로드 → `config/client_secrets.json` 으로 저장
5. 최초 업로드 시 브라우저에서 Google 계정 인증 (1회만)


## Instagram 업로드 설정

1. Instagram을 Business 또는 Creator 계정으로 전환
2. Facebook Page와 연결
3. https://developers.facebook.com 에서 앱 등록
4. instagram_business_content_publish 권한 요청
5. `.env`에 토큰 입력:
```
INSTAGRAM_ACCESS_TOKEN=토큰
INSTAGRAM_USER_ID=사용자ID
```


## 네이버 블로그 업로드 설정

1. https://developers.naver.com 접속
2. 애플리케이션 등록 → 블로그 API 선택
3. `.env`에 입력:
```
NAVER_CLIENT_ID=클라이언트ID
NAVER_CLIENT_SECRET=클라이언트시크릿
```
4. 최초 업로드 시 브라우저에서 네이버 로그인 인증 (1회만)


## 폴더 구조

```
ai2/
├── config/
│   ├── shop_profile.yaml      ← 매장 정보 (수정 필요)
│   ├── schedule.yaml          ← 스케줄 + 주제 큐
│   └── client_secrets.json    ← YouTube OAuth (발급 후 배치)
├── input/
│   ├── blog/
│   │   ├── info.yaml          ← 고객 정보 + 사진 설명
│   │   └── *.jpg              ← 고객 사진
│   └── *.jpg                  ← 영상용 사진
├── output/
│   ├── blog/                  ← 생성된 블로그 글
│   ├── instagram/             ← 생성된 인스타 콘텐츠
│   ├── youtube/videos/        ← 생성된 영상
│   └── logs/                  ← 스케줄 실행 기록
├── src/                       ← 소스 코드
├── .env                       ← API 키 (직접 생성)
├── .env.example               ← API 키 템플릿
└── requirements.txt           ← 패키지 목록
```


## 문제 해결

| 문제 | 해결 |
|------|------|
| 한글 깨짐 | `PYTHONIOENCODING=utf-8` 환경변수 설정 |
| FFmpeg 없음 | `winget install ffmpeg` 실행 |
| API 키 오류 | `python -m src.main setup` 으로 확인 |
| 카카오톡 안 옴 | 토큰 만료 → 재발급 필요 |
| 스케줄 안 돌아감 | PC가 켜져있어야 함. `schtasks /query /tn BeautyAgentNotify` 로 확인 |
