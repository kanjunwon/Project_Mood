# 감정 서가 백엔드

## 셋업

```bash
cd backend
python -m venv .venv          # 또는 conda(base) 환경 그대로 사용해도 무방
source .venv/bin/activate
pip install -r requirements.txt
```

⚠️ **GPU 서버(RunPod 등)에서 실제 모델(`MOCK_MODE=false`)을 돌릴 땐, `requirements.txt`의 `torch` 줄이 그 서버에 이미 설치된 GPU용 torch랑 충돌할 수 있음** (개발 로컬 PC는 GPU가 없어서 `pip freeze`에 CPU/일반 버전이 찍힘). 충돌 나면:
```bash
grep -v "^torch" requirements.txt > requirements_nogpu.txt
pip install -r requirements_nogpu.txt
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.device_count())"
```
GPU 환경에서 `accelerate` 패키지도 필수 (LLaMA GPU 로딩에 필요, `requirements.txt`에 포함되어 있음).

## `.env` 만들기

`backend` 폴더에 `.env` 파일 만들고 채우기 (`.env.example` 참고):

```
MOCK_MODE=false
SUPABASE_URL=
SUPABASE_KEY=
HF_TOKEN=
JWT_SECRET=
COMFYUI_URL=
```

- `MOCK_MODE=true`: 실제 AI 모델(LLaMA/KoBERT) 없이 가짜 응답으로 API 테스트 (GPU 없는 환경에서 개발할 때 사용)
- `MOCK_MODE=false`: 실제 모델 로딩, GPU 필요
- `SUPABASE_URL` / `SUPABASE_KEY`: 재유한테 받은 값
- `HF_TOKEN`: Hugging Face 토큰 (LLaMA 모델 다운로드용, gated 저장소면 모델 페이지에서 라이선스 동의도 필요)
- `JWT_SECRET`: 로그인 토큰 서명용 랜덤 문자열
- `COMFYUI_URL`: ComfyUI 서버 주소 (예: `http://127.0.0.1:8188`, FastAPI랑 ComfyUI가 같은 머신이면 localhost로 충분)

`.env` 파일은 PowerShell heredoc(`@'...'@ | Out-File -Encoding utf8`)이나 `cat > file << 'EOF'` 방식으로 만들 때, 종료 마커가 제대로 안 닫히면 스크립트 줄이 그대로 섞여 들어가는 경우가 있었음 — 만든 후 `cat .env`로 내용 한 번 확인하는 습관 추천.

## KoBERT 모델 파일 준비 (git에는 코드만 있고, 가중치는 별도)

1. 종현이가 공유한 구글드라이브에서 `emotion24_inference.zip` 다운로드
2. 압축 풀고 안의 `model/emotion24-bert` 폴더를 `backend/kobert_model/emotion24-bert`로 복사
3. `emotion_list.py`는 이미 `app/emotion_list.py`로 레포에 포함되어 있음 (모델 출력 순서 매핑용, 절대 수정 금지 - 학습 시 순서 그대로 유지해야 함)

```bash
mkdir -p kobert_model
cp -r [압축 푼 경로]/model/emotion24-bert kobert_model/
```

KoBERT는 GPU 2개 이상인 환경(학교 서버)에서는 `cuda:1`, GPU 1개(RunPod 등)에서는 `cuda:0`을 자동으로 골라 씀 (`torch.cuda.device_count()`로 판단). 수동 설정 필요 없음.

## ComfyUI 준비 (이미지 생성용)

1. ComfyUI를 API 모드로 실행: `python main.py --listen 0.0.0.0 --port 8188`
2. Illustrious XL 체크포인트(`Illustrious-XL-v1.0.safetensors`) + `gamjeong_illustrious_v1.safetensors` LoRA가 ComfyUI 모델 폴더에 있어야 함 (경로는 템플릿마다 다를 수 있음, `find / -type d -iname checkpoints`로 확인)
3. 워크플로우는 `backend/app/comfyui_workflow.json`에 API 형식으로 저장되어 있음 (ComfyUI에서 "Enable Dev mode Options" 켜고 "Save (API Format)"으로 export한 것)
4. `sd3_loader.py`가 로드 시 워크플로우 안에 LoRA 파일명이 실제로 들어있는지 자동 검증함 (다른 워크플로우를 잘못 export해서 넣는 실수 방지)

## 서버 실행

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**`--reload` 옵션은 절대 쓰지 말 것.** 개발 중 재시도 로직이 여러 번 도는 상황에서 서버가 불안정해지는 원인으로 확인됨 (모델이 이미 GPU에 로딩된 상태에서 파일 변경 감지로 재시작되면서 응답이 끊기는 문제로 추정). 로컬 `MOCK_MODE=true` 개발 중에만 `--reload` 써도 무방, `MOCK_MODE=false`(실 모델) 환경에서는 절대 금지.

`http://127.0.0.1:8000/docs` 에서 API 테스트 가능 (Swagger UI). 로그인 필요한 API는 우측 상단 **Authorize** 버튼으로 토큰(`Bearer ` 없이 값만) 등록하면 이후 요청에 자동 적용됨.

## 폴더 구조

```
app/
├── main.py                       # FastAPI 진입점 (CORS, load_dotenv 순서 주의)
├── config.py
├── database.py                   # Supabase 클라이언트 (키 없으면 DB 스킵 모드로 자동 전환)
├── dependencies.py               # JWT 토큰 → user_id 추출 (HTTPBearer, Swagger Authorize 연동)
├── emotion_taxonomy.py           # 24개 감정 분류 체계 + 색상 팔레트 (재유)
├── emotion_list.py               # KoBERT 모델 출력 ID→감정명 매핑 (종현, 수정 금지)
├── personal_test_questions.py    # 퍼스널 검사 19문항(HSP 13 + LOT-R 6) 원문
├── comfyui_workflow.json         # ComfyUI API 형식 워크플로우
├── schemas/
│   ├── diary.py                  # DiaryResponse에 top_emotion/emotion_scores/sentiment_score 포함
│   ├── stats.py
│   ├── auth.py                   # 회원가입 검증(비밀번호 8자+영문/숫자), 비밀번호 변경 스키마 포함
│   ├── profile.py                # 아바타(안경 3종/앞머리/머리길이/머리색)
│   ├── account.py                # 계정 설정(성별/직업/생년월일)
│   └── personal_test.py
├── routers/
│   ├── diary.py                  # 일기 생성 시 KoBERT 감정 분석 + SD3 이미지 생성까지 같이 실행, JWT 필수
│   ├── stats.py                  # /stats/daily/me, /stats/monthly/me, JWT 필수
│   ├── auth.py                   # signup/login
│   ├── profile.py                # GET/PATCH /users/me/profile (아바타)
│   ├── account.py                # 계정 설정, 비밀번호 변경, 탈퇴, 설정화면 요약통계
│   └── personal_test.py          # 검사 제출 + GET /personal-test/status
├── services/
│   ├── llama_service.py          # 호미 - 프롬프트, 검증, 안전 템플릿 폴백 포함
│   ├── image_prompt_service.py   # 일기 텍스트 → 영어 danbooru 태그 프롬프트 변환 (LLM 2차 호출)
│   ├── kobert_service.py         # 실제 24개 감정분류 모델 연동 완료
│   ├── sd3_service.py            # 재유 - ComfyUI API 호출 방식, 아바타(안경 3종 포함) 프롬프트 반영 완료
│   ├── stats_service.py          # 호미
│   └── auth_service.py           # 호미
├── models/
│   ├── llama_loader.py           # torch/transformers lazy import (Mock 모드에서 안 불림)
│   ├── kobert_loader.py          # lazy import, GPU 개수 자동 감지(cuda:0/cuda:1)
│   └── sd3_loader.py             # ComfyUI 워크플로우 JSON 로더 + LoRA 파일명 sanity check (재유)
└── repositories/
    ├── diary_repository.py
    ├── user_repository.py        # 프로필/계정 수정, 비밀번호 변경, 탈퇴(연쇄삭제) 포함
    └── personal_test_repository.py
```

## DB 스키마

- `supabase_schema.sql`: `diary_entries` (감정 분석 컬럼 포함)
- `users_table.sql`: `users` (이메일/비밀번호/닉네임)
- `users`에 이후 추가된 컬럼(재유, 2026-09): `glasses`(text: horn_rimmed/round/none), `bangs`, `hair_length`, `hair_color`(아바타), `gender`, `job`, `birth_date`(계정 설정) — 별도 SQL 파일 없이 SQL Editor에서 직접 `alter table`로 추가함
- `personal_test_results`: 재유가 별도 생성

**RLS는 전부 꺼둔 상태로 운영.** Supabase Auth가 아닌 자체 JWT 로그인 방식이라, 클라이언트가 Supabase를 직접 안 건드리고 항상 백엔드를 거쳐서만 DB에 접근함 → user_id 검증은 백엔드 코드가 전담. 새 테이블 만들 때마다 기본값이 RLS 켜짐이라 매번 꺼줘야 함:
```sql
alter table [테이블명] disable row level security;
```

## API 엔드포인트

### 인증
- `POST /signup` — 이메일/비밀번호(8~64자, 영문+숫자 포함)/닉네임(2~20자)로 회원가입, JWT 토큰 즉시 발급, 이메일 중복이면 `409`
- `POST /login` — 로그인, JWT 토큰 발급

> ⚠️ **아래 API는 전부 `Authorization: Bearer <토큰>` 헤더 필수.** `user_id`를 body/path로 직접 안 받고 토큰에서만 가져옴 (2026-09-16부로 `/diaries`, `/stats/*`도 포함해서 전체 통일 완료).

### 일기
- `POST /generate-diary`

**Request**
```json
{
  "what": "카페에서 과제 하기", "why": "...", "who": ["혼자"],
  "when": "주말 오후 2시", "where": "집 앞 카페"
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
  "sentiment_score": 0.6,
  "image_url": "https://.../diary-images/xxxx.png"
}
```
일기 생성(LLM) → KoBERT 감정 분석 → 이미지 프롬프트 변환(LLM) → ComfyUI 이미지 생성 → Supabase Storage 업로드 → DB 저장까지 한 번에 처리됨. 로그인한 사용자의 아바타 설정(안경/앞머리/머리길이/머리색)이 이미지 생성 프롬프트에 자동 반영됨. RunPod(RTX A6000) 실 GPU 환경에서 전체 흐름 검증 완료 (2026-09-16).

- `GET /diaries/me` — 로그인한 본인 일기 목록 조회

### 통계
- `GET /stats/daily/me?date=YYYY-MM-DD`, `GET /stats/monthly/me?year=&month=` — 24개 감정 기준 통계, `emotion_distribution`에 재유가 정한 8개 중분류 색상 + 긍정/부정(valence) 자동 매핑됨

### 퍼스널 감정 검사
- `POST /personal-test` — HSP 13문항 + LOT-R 6문항 응답 제출. 결과는 사용자에게 노출하지 않고 내부 저장만 함. **`weight_profile` 계산 알고리즘은 아직 미완성** — 종현이가 KoBERT 실제 테스트로 감정 비율 기준을 잡는 중이라, 그 결과 나오면 설계 예정. 재제출하면 새 row로 쌓이고 가장 최근 것이 "현재" 결과로 취급됨
- `GET /personal-test/status` — 이 사용자가 검사를 완료했는지 확인. **회원가입 직후 필수로 검사받도록 프론트에서 이걸로 분기 처리하기로 함**

### 아바타 프로필
- `GET/PATCH /users/me/profile` — 안경(`glasses`: `"horn_rimmed"` / `"round"` / `"none"`, 2026-09-16부로 boolean에서 변경됨)/앞머리(`bangs`)/머리길이(`hair_length`: short/medium/long)/머리색(`hair_color`: 자유 문자열, 한국어/영어 웬만큼 매핑됨)

### 계정 설정
- `GET/PATCH /users/me/account` — 성별/직업/생년월일
- `PATCH /users/me/password` — 현재 비밀번호 확인 후 변경
- `DELETE /users/me` — 계정탈퇴 (diary_entries, personal_test_results까지 연쇄 삭제)
- `GET /users/me/stats` — 설정 화면 상단 요약카드용 ("감정 기록 시작한 지 N Days", "기록한 감정 N Emotion")

---

## 🔧 트러블슈팅 노트 (겪었던 문제들, 다음에 또 겪지 않기 위한 기록)

### "Name or service not known" / DB 저장 실패
학교 네트워크가 Supabase 도메인을 막아둔 경우가 있음. `curl -I [SUPABASE_URL]`로 먼저 확인. 안 되면 핫스팟으로 네트워크 전환해서 재시도.

### "521: Web server is down" (Supabase)
Supabase 무료 플랜은 오래 안 쓰면 프로젝트가 자동으로 일시정지(Paused)됨. **프로젝트 소유자만 Restore 가능** (협업자 권한으로는 안 됨) - 재유한테 요청해야 함.

### 회원가입 시 500 에러 - bcrypt/passlib 버전 충돌
`passlib`이 최신 `bcrypt`(4.1+)의 내부 속성을 못 찾아서 나는 문제. `requirements.txt`에 `bcrypt==4.0.1`로 고정되어 있어야 함.

### RunPod GPU 서버 - `invalid device ordinal` (KoBERT)
GPU 1개짜리 환경에서 `cuda:1`을 하드코딩해서 쓰면 발생. `kobert_loader.py`가 `torch.cuda.device_count()`로 자동 판단하도록 2026-09-16에 수정 완료 — 더 이상 수동 조치 필요 없음.

### RunPod GPU 서버 - `torch==X.X.X` 설치 충돌
로컬 개발 PC(GPU 없음)에서 `pip freeze`한 `requirements.txt`의 torch 버전이, GPU 서버에 이미 깔린 torch(CUDA 버전 맞춰진 것)랑 충돌함. 위 "셋업" 섹션의 `requirements_nogpu.txt` 방법으로 우회.

### RunPod GPU 서버 - `accelerate` 없다는 에러
LLaMA 모델을 GPU로 로딩할 때 device_map 관련 기능에 `accelerate` 패키지가 필요. `requirements.txt`에 포함해뒀음 (2026-09-16 추가).

### RunPod Pod 재시작 시 매번 `pip install` 필요
`/workspace`(모델 파일, git 레포, `.env`)는 Stop/Start해도 유지되지만, 컨테이너에 직접 설치한 파이썬 패키지는 컨테이너와 함께 초기화됨. Pod 켤 때마다 `pip install -r requirements.txt` 다시 필요.

### RunPod 컨테이너 안에서 직접 고친 코드는 git에 반영 안 됨 (중요)
RunPod 컨테이너 안에서 `sed`나 직접 파일 수정으로 버그를 고쳐도, git commit/push를 안 하면 **그 컨테이너 안에서만 유효**하고 저장소엔 반영이 안 됨. Pod을 새로 만들거나 다른 사람이 pull 받으면 똑같은 버그를 처음부터 다시 겪게 됨. **RunPod에서 뭔가 고치면, 그 내용을 로컬 PC(또는 RunPod에서 직접)로 커밋/푸시까지 해야 진짜 해결된 것.**

### `.env`/`requirements.txt` 파일이 Windows에서 이상하게 깨짐
PowerShell의 `echo "내용" >> file`이 UTF-16으로 저장하는 경우가 있어서, 파일 안 텍스트 사이에 널바이트(`\x00`)가 섞여 pip/파서가 못 읽는 문제 발생. `Add-Content -Path file -Value "내용" -Encoding utf8`처럼 인코딩을 명시하거나, PowerShell heredoc(`@'...'@ | Out-File -Encoding utf8`) 사용 권장.

### 안드로이드 앱 - 로컬 백엔드 연결
- `ApiClient.kt`의 `BASE_URL`이 `10.0.2.2`(에뮬레이터 전용)로 되어있으면 에뮬레이터에서만 작동, 실제 기기는 실제 네트워크 IP로 교체 필요
- 학교 Wi-Fi는 기기 간 통신을 막아두는 경우(AP Isolation)가 많음 → 안 되면 핫스팟으로 우회
- 방화벽 포트 개방 필요: `sudo ufw allow 8000` (ComfyUI 쓰면 `8188`도)
- **2026-09-09부로 로그인 필수 API가 크게 늘었고, 2026-09-16부로 `/diaries`, `/stats/*`도 포함됨** — 모든 요청에 `Authorization: Bearer <토큰>` 헤더 필요, `user_id`를 URL에 넣는 옛날 방식은 전부 제거됨

### 리눅스에서 Android 앱 빌드 (Android Studio 없이)
```bash
sudo apt install openjdk-17-jdk
export ANDROID_HOME=~/android-sdk
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator
sdkmanager "platform-tools" "platforms;android-34" "build-tools;34.0.0"
cd frontend
chmod +x gradlew
./gradlew assembleDebug
```

### LLaMA 프롬프트 - 방향(소유격) 헷갈림
"친구네 집"처럼 소유격이 들어간 장소 정보를 줬을 때, 모델이 방향을 반대로 뒤집어서 쓰는 경우 발견. `llama_service.py`에 명시적 규칙 + few-shot 예시 추가해서 해결.

### LLaMA 프롬프트 - 지어내기 위험도 구분
"저위험(흔한 배경 묘사는 허용) vs 고위험(결과/판단, 술, 식사시간대, 대화내용은 절대 금지)"으로 구분해서 지시. 완전히 0%는 안 됨 - 10.8B 모델의 구조적 한계.

### KoBERT - MAX_LEN 잘림 버그
`MAX_LEN=64`였을 때 실제 일기(3~5문장)가 잘려서 긍정적 마무리가 안 보이는 문제 있었음. `128`로 늘려서 개선, 완벽하진 않음(재학습 시 더 긴 max_length 고려 필요).

### RunPod 등 GPU 클라우드 최종 체크리스트
1. `requirements_nogpu.txt`로 설치 후 `torch.cuda.is_available()`, `device_count()` 확인
2. `kobert_model/emotion24-bert` 폴더 업로드
3. ComfyUI 체크포인트 + LoRA 모델 폴더에 배치, `.env`의 `COMFYUI_URL` 설정
4. `--reload` 절대 금지
5. 테스트 끝나면 Pod **Stop** (과금 방지, Terminate는 금지 — 모델 파일 다 날아감)
6. 컨테이너 안에서 고친 거 있으면 **꼭 git commit/push**
