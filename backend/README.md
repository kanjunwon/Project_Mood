# 감정 서가 백엔드

## 셋업

```bash
cd backend
python -m venv .venv          # 또는 conda(base) 환경 그대로 사용해도 무방
source .venv/bin/activate
pip install -r requirements.txt
```

## `.env` 만들기

`backend` 폴더에 `.env` 파일 만들고 채우기 (`.env.example` 참고):

```
MOCK_MODE=false
SUPABASE_URL=
SUPABASE_KEY=
HF_TOKEN=
JWT_SECRET=
```

- `MOCK_MODE=true`: 실제 AI 모델(LLaMA/KoBERT) 없이 가짜 응답으로 API 테스트 (GPU 없는 환경에서 개발할 때 사용)
- `MOCK_MODE=false`: 실제 모델 로딩, GPU 필요
- `SUPABASE_URL` / `SUPABASE_KEY`: 재유한테 받은 값
- `HF_TOKEN`: Hugging Face 토큰 (LLaMA 모델 다운로드용)
- `JWT_SECRET`: 로그인 토큰 서명용 랜덤 문자열

## KoBERT 모델 파일 준비 (git에는 코드만 있고, 가중치는 별도)

1. 종현이가 공유한 구글드라이브에서 `emotion24_inference.zip` 다운로드
2. 압축 풀고 안의 `model/emotion24-bert` 폴더를 `backend/kobert_model/emotion24-bert`로 복사
3. `emotion_list.py`는 이미 `app/emotion_list.py`로 레포에 포함되어 있음 (모델 출력 순서 매핑용, 절대 수정 금지 - 학습 시 순서 그대로 유지해야 함)

```bash
mkdir -p kobert_model
cp -r [압축 푼 경로]/model/emotion24-bert kobert_model/
```

## 서버 실행

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**`--reload` 옵션은 절대 쓰지 말 것.** 개발 중 재시도 로직이 여러 번 도는 상황에서 서버가 불안정해지는 원인으로 확인됨 (모델이 이미 GPU에 로딩된 상태에서 파일 변경 감지로 재시작되면서 응답이 끊기는 문제로 추정).

`http://127.0.0.1:8000/docs` 에서 API 테스트 가능 (Swagger UI)

## 폴더 구조

```
app/
├── main.py                       # FastAPI 진입점 (CORS, load_dotenv 순서 주의)
├── config.py
├── database.py                   # Supabase 클라이언트 (키 없으면 DB 스킵 모드로 자동 전환)
├── emotion_taxonomy.py           # 24개 감정 분류 체계 + 색상 팔레트 (재유)
├── emotion_list.py               # KoBERT 모델 출력 ID→감정명 매핑 (종현, 수정 금지)
├── schemas/
│   ├── diary.py                  # DiaryResponse에 top_emotion/emotion_scores/sentiment_score 포함
│   ├── stats.py
│   ├── auth.py
│   └── personal_test.py
├── routers/
│   ├── diary.py                  # 일기 생성 시 KoBERT 감정 분석도 같이 실행
│   ├── stats.py
│   ├── auth.py
│   └── personal_test.py
├── services/
│   ├── llama_service.py          # 호미 - 프롬프트, 검증, 안전 템플릿 폴백 포함
│   ├── kobert_service.py         # 실제 24개 감정분류 모델 연동 완료
│   ├── ad3_service.py            # (미사용, sd3_service.py로 대체)
│   ├── sd3_service.py            # 재유 - ComfyUI API 호출 방식 (진행 중, 화풍 조정 중)
│   ├── stats_service.py          # 호미
│   └── auth_service.py           # 호미
├── models/
│   ├── llama_loader.py           # torch/transformers lazy import (Mock 모드에서 안 불림)
│   ├── kobert_loader.py          # 마찬가지로 lazy import, cuda:1 고정
│   └── sd3_loader.py             # ComfyUI 워크플로우 JSON 로더 (재유)
└── repositories/
    ├── diary_repository.py
    ├── user_repository.py
    └── personal_test_repository.py
```

## DB 스키마

- `supabase_schema.sql`: `diary_entries` (감정 분석 컬럼 포함)
- `users_table.sql`: `users`
- `personal_test_results`: 재유가 별도 생성

**RLS는 전부 꺼둔 상태로 운영.** Supabase Auth가 아닌 자체 JWT 로그인 방식이라, 클라이언트가 Supabase를 직접 안 건드리고 항상 백엔드를 거쳐서만 DB에 접근함 → user_id 검증은 백엔드 코드가 전담. 새 테이블 만들 때마다 기본값이 RLS 켜짐이라 매번 꺼줘야 함:
```sql
alter table [테이블명] disable row level security;
```

## API 엔드포인트

### POST `/signup`, POST `/login`
이메일/비밀번호 회원가입·로그인, JWT 토큰 발급

### POST `/generate-diary`
**Request**
```json
{
  "what": "카페에서 과제 하기", "why": "...", "who": ["혼자"],
  "when": "주말 오후 2시", "where": "집 앞 카페", "user_id": "선택사항"
}
```
**Response**
```json
{
  "status": "success",
  "generated_diary": "...",
  "validation_failed": false,
  "top_emotion": "편안한",
  "emotion_scores": { "행복한": 0.05, "편안한": 0.4, ... 24개 전부 },
  "sentiment_score": 0.6
}
```
일기 생성 → KoBERT 감정 분석 → DB 저장까지 한 번에 처리됨.

### GET `/diaries/{user_id}`

### GET `/stats/daily/{user_id}?date=YYYY-MM-DD`, GET `/stats/monthly/{user_id}?year=&month=`
24개 감정 기준 통계, `emotion_distribution`에 재유가 정한 8개 중분류 색상 자동 매핑됨

### POST `/personal-test`
퍼스널 감정 검사(HSP 13문항 + LOT-R 6문항) 응답 제출. 결과는 사용자에게 노출하지 않고 내부 저장만 함 (`weight_profile` 계산 로직은 미완성, TODO로 남아있음).

---

## 🔧 트러블슈팅 노트 (겪었던 문제들, 다음에 또 겪지 않기 위한 기록)

### "Name or service not known" / DB 저장 실패
학교 네트워크가 Supabase 도메인을 막아둔 경우가 있음. `curl -I [SUPABASE_URL]`로 먼저 확인. 안 되면 핫스팟으로 네트워크 전환해서 재시도.

### "521: Web server is down" (Supabase)
Supabase 무료 플랜은 오래 안 쓰면 프로젝트가 자동으로 일시정지(Paused)됨. **프로젝트 소유자만 Restore 가능** (협업자 권한으로는 안 됨) - 재유한테 요청해야 함. Restore 후에도 DNS/서버가 완전히 뜨는 데 몇 분 걸릴 수 있음.

### 안드로이드 앱 - 로컬 백엔드 연결
- `ApiClient.kt`의 `BASE_URL`이 `10.0.2.2`(에뮬레이터 전용, 호스트 PC의 127.0.0.1을 가리킴)로 되어있으면 에뮬레이터에서만 작동
- 실제 기기나 다른 PC에서 접속하려면 실제 네트워크 IP로 교체 필요 (`hostname -I` 또는 `ip route get 8.8.8.8`로 확인)
- 학교 Wi-Fi는 기기 간 통신을 막아두는 경우(AP Isolation)가 많음 → 안 되면 핫스팟으로 우회
- 방화벽 포트 개방 필요: `sudo ufw allow 8000`

### 리눅스에서 Android 앱 빌드 (Android Studio 없이)
```bash
sudo apt install openjdk-17-jdk
# Android SDK cmdline-tools 설치 후
export ANDROID_HOME=~/android-sdk
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator
sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0"
cd frontend
chmod +x gradlew   # 권한 없으면 빌드 자체가 안 됨
./gradlew assembleDebug
```
에뮬레이터가 필요하면 `system-images;android-34;google_apis;x86_64` 추가 설치 후 `avdmanager create avd`.

### 프론트-백엔드 연결 관련 (진행 중 이슈)
`ApiClient`는 만들어져 있어도, 실제 화면(버튼 클릭 등)에서 `emotionApi.generateDiary(...)`를 호출하는 코드가 아직 연결 안 된 경우가 있었음. 코드에 API 클라이언트가 존재하는 것과, 실제로 호출되는 것은 다르니 `grep -rn "emotionApi\." app/src`로 실제 호출부가 있는지 확인 필요.

### LLaMA 프롬프트 - 방향(소유격) 헷갈림
"친구네 집"처럼 소유격이 들어간 장소 정보를 줬을 때, 모델이 방향을 반대로 뒤집어서 쓰는 경우 발견 (예: "친구 집에 갔다"를 "친구가 우리 집에 왔다"로 왜곡). `llama_service.py`에 명시적 규칙 + few-shot 예시 추가해서 해결. 비슷한 소유격 상황(부모님 댁, 회사 등) 새로 추가할 때도 방향 명확한 예시를 few-shot에 넣어주는 게 안전함.

### LLaMA 프롬프트 - 지어내기 위험도 구분
"지어내지 마라"를 카테고리 나열식으로 계속 추가하는 방식은 한계가 있음(무한히 늘어남). 대신 "저위험(흔한 배경 묘사는 허용) vs 고위험(결과/판단, 술, 식사시간대, 대화내용은 절대 금지)"으로 구분해서 지시하는 방식으로 전환. 닫힌 어휘(술 종류, 식사시간대, 관계호칭)는 코드로 자동 검증 가능하지만, 열린 카테고리(대화 주제, 결과 판단 등)는 프롬프트+낮은 temperature+안전 템플릿 폴백으로만 감수 가능. 완전히 0%는 안 됨 - 10.8B 모델의 구조적 한계로 보임.

### KoBERT - MAX_LEN 잘림 버그 (중요, 발견 및 수정)
`infer.py` 원본의 `MAX_LEN=64`를 그대로 썼더니, 실제 일기(3~5문장, 90~250자)는 토큰 수가 64를 훌쩍 넘어서(예: 93토큰) **뒷부분이 통째로 잘려나가는 문제** 발견. 특히 일기가 부정적인 사건으로 시작해서 긍정적으로 마무리되는 경우, 그 긍정적 마무리가 잘려서 안 보이니 감정이 완전히 반대로 분류됨 (예: "피곤했지만... 재밌었다" 같은 문장에서 "재밌었다"가 잘려 "피곤한"으로만 판단).

`kobert_loader.py`에서 `MAX_LEN`을 128로 늘려서 개선됨. **단, 모델이 학습할 때도 64로 잘렸다면 65번째 토큰 이후는 학습 안 된 위치라 완벽하지 않을 수 있음 - 종현이한테 학습 시 max_length도 확인 요청 필요.** 여전히 완벽하진 않고(예: "피곤한"에 과민 반응하는 경향 일부 남아있음), 재학습 시 더 긴 max_length로 다시 돌리면 개선 가능성 있음.