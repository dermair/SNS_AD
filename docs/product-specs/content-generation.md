# 콘텐츠 생성 기능 스펙

## CLI 명령어

### `setup`
- 피부관리실 프로필(config/shop_profile.yaml) 로딩 확인
- API 키(.env) 설정 확인

### `generate <주제>`
- 주제를 분석하여 3개 플랫폼 콘텐츠 동시 생성
- `--platform` 옵션으로 특정 플랫폼만 지정 가능
- `--video` 옵션으로 영상 생성 포함

### `list`
- output/ 폴더의 생성��� 콘텐츠 목록 표시

### `review`
- 가장 최근 생성된 콘텐츠를 터미널에서 미리보기

## 생성 워크플로우

1. **입력**: 사용자가 주제/키워드 입력 (��: "여드름관리 봄 프로모션")
2. **분석**: Orchestrator가 Claude로 주제 분석 + 전략 수립
3. **생성**: 플랫폼별 에이전트가 병렬로 콘텐츠 생성
   - Blog Agent → Claude/GPT → 텍스트 + Gemini → 썸네일
   - Instagram Agent → GPT → 캡션 + Gemini → 이미지
   - YouTube Agent → Claude → 스크립트 + Kling → 영상
4. **포맷팅**: ��랫폼별 포맷터가 출력 형식 변환
5. **저장**: output/ 폴더에 파일로 저장
6. **검수**: 사용자가 터미널 또는 파일에서 확인 후 수정
7. **��로드**: 사용자가 각 플랫폼에 직접 업로드

## 출력 파일 형식

| 플랫폼 | 파일 | 내용 |
|--------|------|------|
| 블로그 | `blog_YYYYMMDD_HHMMSS.md` | 제목+본문+태그+SEO |
| 인스타 | `instagram_YYYYMMDD_HHMMSS.md` | 전체 정보 |
| 인스타 | `caption_YYYYMMDD_HHMMSS.txt` | 캡션+해시태그 (복사용) |
| 유튜브 | `youtube_YYYYMMDD_HHMMSS.md` | 전체 정보 |
| 유튜브 | `script_YYYYMMDD_HHMMSS.txt` | 스크립트 (복사용) |

## 피부관리 콘텐츠 특수 규칙

- 의료 행위 암시 표현 자동 필터 (진단, 치료, 처방 등)
- 피부 고민별 키워드 자동 추천 (여드름, 모공, 주름, 색소 등)
- 홈케어 팁 자동 포함 (관리 전후 주의사항)
