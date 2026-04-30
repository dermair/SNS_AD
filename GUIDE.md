# 홍보 에이전트 — 최종 가이드

주제 하나만 입력하면 블로그, 인스타그램, 유튜브 콘텐츠를 자동으로 만들어주는 AI 에이전트입니다.
영상도 자동으로 만들고, 카카오톡으로 알림도 받고, 각 플랫폼에 업로드까지 할 수 있습니다.


---


## 처음 설치하기 (10분)


### 1. Python 설치

- https://www.python.org/downloads/ 에서 최신 버전 다운로드
- 설치할 때 반드시 "Add Python to PATH" 체크하세요
- 설치 후 확인:
```
python --version
```


### 2. FFmpeg 설치 (영상 편집용)

관리자 권한으로 터미널(PowerShell)을 열고:
```
winget install ffmpeg
```
설치 후 확인:
```
ffmpeg -version
```


### 3. 프로젝트 패키지 설치

프로젝트 폴더로 이동해서:
```
cd C:\Users\사용자이름\Desktop\ai2
pip install -r requirements.txt
```


### 4. API 키 설정

`.env.example` 파일을 복사합니다:
```
copy .env.example .env
```

`.env` 파일을 메모장으로 열어서 API 키를 입력하세요.

최소 3개만 있으면 바로 사용 가능합니다:

| API | 어디서 발급? | 비용 |
|-----|-------------|------|
| Claude API | https://console.anthropic.com → API Keys 생성 | 사용량 과금 |
| OpenAI API | https://platform.openai.com → API Keys 생성 | 사용량 과금 |
| Google Gemini | https://aistudio.google.com/apikey → 키 생성 | 무료 |

발급받은 키를 `.env` 파일에 붙여넣기:
```
ANTHROPIC_API_KEY=발급받은키
OPENAI_API_KEY=발급받은키
GOOGLE_API_KEY=발급받은키
```


### 5. 매장 정보 설정

예시 파일을 복사합니다:
```
copy config\shop_profile.example.yaml config\shop_profile.yaml
```

`config/shop_profile.yaml` 파일을 열어서 본인 매장 정보로 수정하세요:
- 매장 이름, 주소, 전화번호
- 인스타/블로그/유튜브 계정
- 시술 메뉴와 가격
- 영업시간
- 프로모션 정보


### 6. 설치 확인

```
python -m src.main setup
```

매장 정보와 API 키 상태가 정상으로 표시되면 준비 완료입니다.


---


## 기본 사용법


### 콘텐츠 한번에 생성하기

주제만 입력하면 블로그 + 인스타 + 유튜브 콘텐츠가 동시에 만들어집니다:
```
python -m src.main generate "여드름 관리 후기"
```

블로그만 만들고 싶으면:
```
python -m src.main generate "모공 관리 후기" -p blog
```

인스타만:
```
python -m src.main generate "수분 관리 소개" -p instagram
```


### 결과물 확인하기

생성된 콘텐츠 목록 보기:
```
python -m src.main list
```

최근 콘텐츠 미리보기:
```
python -m src.main review
```

카카오톡으로 받아보기:
```
python -m src.main kakao -p blog
python -m src.main kakao -p instagram
python -m src.main kakao -p youtube
```

파일 직접 열기:
```
output\blog\          블로그 글 (.md 파일)
output\instagram\     인스타 캡션 + 해시태그
output\youtube\       유튜브 스크립트
output\youtube\videos\  영상 파일 (.mp4)
```


---


## 고객 정보로 블로그 글 쓰기

고객 사진과 정보를 넣으면 맞춤형 블로그 글이 생성됩니다.


### 1단계: 고객 정보 입력

`input/blog/info.yaml` 파일을 열어서 수정하세요:

```yaml
topic: "여드름 관리 후기"
customers:
  - name: "A고객님"
    age: "20대 후반"
    concern: "볼과 턱 라인 반복 여드름"
    how_found: "인스타 보고 방문"
    result: "3회 케어 후 붉음증 개선"
    review_quote: "피부가 차분해진 느낌이에요"
    photos:
      before: "before_1.jpg"
      after: "after_1.jpg"
```


### 2단계: 사진 넣기

`input/blog/` 폴더에 사진을 넣으세요:
```
input/blog/
├── info.yaml
├── before_1.jpg     A고객 케어 전
├── after_1.jpg      A고객 케어 후
├── review_1.jpg     A고객 후기 캡처
├── before_2.jpg     B고객 케어 전
└── after_2.jpg      B고객 케어 후
```


### 3단계: 글 생성

```
python -m src.main generate "여드름 관리 후기" -p blog
```

고객 정보와 사진 위치가 자동으로 글에 반영됩니다.


---


## 영상 자동 편집

사진을 넣으면 유튜브 쇼츠 / 인스타 릴스 영상이 자동으로 만들어집니다.


### 1단계: 사진 넣기

`input/` 폴더에 사진을 넣으세요 (jpg, png).


### 2단계: 영상 생성

스크립트(자막) 미리보기가 먼저 나오고, 확인 후 영상이 만들어집니다.

슬라이드쇼 (사진 + 자막):
```
python -m src.main shorts -i ./input/ -t "여드름 케어 전후"
```

AI 나레이션 (사진 + 음성 + 자막):
```
python -m src.main shorts -i ./input/ -t "여드름 케어 전후" -m narration
```

BGM 추가:
```
python -m src.main shorts -i ./input/ -t "여드름 케어 전후" --bgm music.mp3
```


### 3단계: 확인

`output/youtube/videos/` 폴더에서 영상을 재생해서 확인하세요.


---


## 플랫폼에 업로드하기

생성된 콘텐츠를 각 플랫폼에 올릴 수 있습니다.

```
python -m src.main upload -p youtube      YouTube
python -m src.main upload -p instagram    Instagram
python -m src.main upload -p blog         네이버 블로그
```

업로드 전에 미리보기가 나오고, 확인(y) 후 업로드됩니다.

각 플랫폼 업로드를 사용하려면 추가 설정이 필요합니다 (아래 '플랫폼별 업로드 설정' 참고).


---


## 매일 자동 실행 (스케줄)

매일 09:00에 자동으로 콘텐츠를 생성하고 카카오톡으로 결과를 보내줍니다.


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


### 자동화 등록

`config/schedule_register.bat` 파일을 마우스 우클릭 → 관리자 권한으로 실행


### 자동 실행 흐름

```
매일 09:00
  → 카카오톡: "콘텐츠 생성 시작합니다"
  → AI가 자동으로 콘텐츠 생성
  → 카카오톡: 생성된 콘텐츠 전문 전송
  → 카카오톡: "확인 후 업로드하세요"
  → 카카오톡에서 내용 확인
  → OK면 업로드 명령 실행
```


### 스케줄 관리 명령

```
python -m src.main schedule status          오늘 할 일 + 주간 스케줄 확인
python -m src.main schedule auto            수동으로 오늘 작업 실행
python -m src.main schedule add-topic "주제"  주제 큐에 추가
```

주제 큐가 비면 AI가 시술 메뉴를 기반으로 자동 생성합니다.

스케줄과 주제는 `config/schedule.yaml` 에서 수정할 수 있습니다.


---


## 플랫폼별 업로드 설정

콘텐츠 생성은 위의 3개 API 키만 있으면 되지만, 각 플랫폼에 자동 업로드하려면 추가 설정이 필요합니다.


### 카카오톡 알림

1. https://developers.kakao.com 접속 → 앱 등록
2. 카카오로그인 → 사용설정 ON
3. 카카오로그인 → 동의항목 → talk_message 설정
4. 카카오로그인 → Redirect URI: `http://localhost:3000/callback` 등록
5. 카카오로그인 → 고급 → Client Secret 확인
6. 브라우저에서 아래 주소 열기 (REST_API키 교체):
```
https://kauth.kakao.com/oauth/authorize?client_id=REST_API키&redirect_uri=http://localhost:3000/callback&response_type=code&scope=talk_message
```
7. 카카오 로그인 → 동의 → 주소창에서 `code=` 뒤의 값 복사
8. 터미널에서 토큰 교환 (REST_API키, Client_Secret, 복사한코드 교체):
```
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
9. 출력된 토큰을 `.env`에 입력:
```
KAKAO_CHANNEL_TOKEN=출력된토큰
```


### YouTube 업로드

1. https://console.cloud.google.com 접속 → 프로젝트 생성
2. YouTube Data API v3 활성화
3. 사용자 인증 정보 → OAuth 2.0 클라이언트 ID 생성 (데스크톱 앱)
4. JSON 파일 다운로드 → `config/client_secrets.json` 으로 저장
5. 최초 업로드 시 브라우저에서 Google 계정 인증 (1회만 하면 됨)


### Instagram 업로드

1. Instagram 앱에서 Business 또는 Creator 계정으로 전환
2. Facebook Page 생성 후 Instagram과 연결
3. https://developers.facebook.com 에서 앱 등록
4. instagram_business_content_publish 권한 요청
5. Access Token과 Instagram User ID 발급
6. `.env`에 입력:
```
INSTAGRAM_ACCESS_TOKEN=발급받은토큰
INSTAGRAM_USER_ID=사용자ID
```


### 네이버 블로그 업로드

1. https://developers.naver.com 접속 → 애플리케이션 등록
2. 사용 API: 블로그 선택
3. Client ID와 Client Secret 복사
4. `.env`에 입력:
```
NAVER_CLIENT_ID=클라이언트ID
NAVER_CLIENT_SECRET=클라이언트시크릿
```
5. 최초 업로드 시 브라우저에서 네이버 로그인 인증 (1회만)


---


## 전체 명령어 모음

| 명령 | 설명 |
|------|------|
| `python -m src.main setup` | 설정 확인 |
| `python -m src.main generate "주제"` | 3개 플랫폼 콘텐츠 생성 |
| `python -m src.main generate "주제" -p blog` | 블로그만 생성 |
| `python -m src.main generate "주제" -p instagram` | 인스타만 생성 |
| `python -m src.main generate "주제" -g style.txt` | 추가 지침 적용 |
| `python -m src.main shorts -i ./input/ -t "주제"` | 슬라이드쇼 영상 |
| `python -m src.main shorts -i ./input/ -m narration` | 나레이션 영상 |
| `python -m src.main shorts -i ./input/ --bgm music.mp3` | BGM 영상 |
| `python -m src.main upload -p youtube` | YouTube 업로드 |
| `python -m src.main upload -p instagram` | Instagram 업로드 |
| `python -m src.main upload -p blog` | 네이버 블로그 업로드 |
| `python -m src.main kakao -p blog` | 카카오톡으로 블로그 전송 |
| `python -m src.main kakao -p instagram` | 카카오톡으로 인스타 전송 |
| `python -m src.main kakao -p youtube` | 카카오톡으로 유튜브 전송 |
| `python -m src.main schedule status` | 스케줄 상태 확인 |
| `python -m src.main schedule auto` | 오늘 작업 자동 실행 |
| `python -m src.main schedule run` | 오늘 작업 수동 실행 |
| `python -m src.main schedule add-topic "주제"` | 주제 추가 |
| `python -m src.main list` | 생성된 콘텐츠 목록 |
| `python -m src.main review` | 최근 콘텐츠 미리보기 |


---


## 폴더 구조

```
ai2/
├── config/
│   ├── shop_profile.yaml          본인 매장 정보 (직접 생성)
│   ├── shop_profile.example.yaml  매장 정보 예시
│   ├── schedule.yaml              주간 스케줄 + 주제 큐
│   ├── schedule_register.bat      Windows 스케줄러 등록
│   └── client_secrets.json        YouTube OAuth (발급 후 배치)
├── input/
│   ├── blog/
│   │   ├── info.yaml              고객 정보 + 사진 설명
│   │   └── *.jpg                  고객 사진
│   └── *.jpg                      영상용 사진
├── output/
│   ├── blog/                      블로그 글
│   ├── instagram/                 인스타 콘텐츠
│   ├── youtube/
│   │   ├── *.md                   스크립트
│   │   └── videos/                영상 파일
│   └── logs/                      스케줄 실행 기록
├── src/                           소스 코드 (수정 불필요)
├── .env                           API 키 (직접 생성, 공유 안 됨)
├── .env.example                   API 키 템플릿
├── requirements.txt               패키지 목록
├── README.md                      기술 문서
└── GUIDE.md                       이 가이드
```


---


## 문제가 생겼을 때

| 문제 | 해결 |
|------|------|
| python 명령이 안 됨 | Python 설치 시 "Add to PATH" 체크했는지 확인. 터미널 재시작 |
| pip install 오류 | `python -m pip install -r requirements.txt` 로 시도 |
| 한글이 깨짐 | 터미널에서 `set PYTHONIOENCODING=utf-8` 입력 후 다시 실행 |
| FFmpeg 없다는 오류 | `winget install ffmpeg` 실행 후 터미널 재시작 |
| API 키 오류 | `python -m src.main setup` 으로 어떤 키가 문제인지 확인 |
| 카카오톡이 안 옴 | 토큰 만료됨. 카카오톡 설정 과정을 다시 진행해서 새 토큰 발급 |
| 스케줄이 안 돌아감 | PC가 켜져있어야 함. bat 파일을 관리자 권한으로 다시 실행 |
| 블로그 글이 이상함 | `config/shop_profile.yaml` 의 매장 정보와 blog_guidelines 확인 |
| 영상 자막이 안 보임 | 영상 파일을 재생기로 열어서 확인. 자막은 영상에 내장됨 |
