# 감정 서가 백엔드

## 셋업

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## `.env` 만들기

`backend` 폴더에 `.env` 파일 만들고 아래 내용 채우기 (`.env.example` 참고):

```
MOCK_MODE=true
SUPABASE_URL=
SUPABASE_KEY=
HF_TOKEN=
JWT_SECRET=
```

- `MOCK_MODE=true`: 실제 AI 모델 없이 가짜 응답으로 API 테스트 가능 (로컬 개발용)
- `SUPABASE_URL` / `SUPABASE_KEY`: 없어도 서버는 켜지고, DB 저장만 스킵됨
- `HF_TOKEN`: Hugging Face 토큰 (MOCK_MODE=false로 실제 모델 쓸 때만 필요)
- `JWT_SECRET`: 로그인 토큰 서명용 아무 랜덤 문자열 (로컬 개발 단계에선 아무 값이나 괜찮음)

## 서버 실행

```powershell
python -m uvicorn app.main:app --reload
```

`http://127.0.0.1:8000/docs` 에서 API 테스트 가능 (Swagger UI)

## 폴더 구조

```
app/
├── main.py                       # FastAPI 진입점 (CORS 설정 포함)
├── config.py                     # 환경변수 로딩
├── database.py                   # Supabase 클라이언트 (키 없으면 자동으로 DB 스킵 모드)
├── emotion_taxonomy.py           # 24개 감정 분류 체계
├── schemas/                       # API 요청/응답 형태
│   ├── diary.py
│   ├── stats.py
│   ├── auth.py
│   └── personal_test.py
├── routers/                        # 엔드포인트
│   ├── diary.py
│   ├── stats.py
│   ├── auth.py
│   └── personal_test.py
├── services/                        # AI 모델 / 비즈니스 로직
│   ├── llama_service.py
│   ├── kobert_service.py
│   ├── ad3_service.py
│   ├── stats_service.py
│   └── auth_service.py
├── models/                          # AI 모델 로더 (싱글톤)
│   ├── llama_loader.py
│   ├── kobert_loader.py
│   └── ad3_loader.py
└── repositories/                     # DB 읽기/쓰기
    ├── diary_repository.py
    ├── user_repository.py
    └── personal_test_repository.py
```

## DB 스키마

- `supabase_schema.sql`: `diary_entries` 테이블 (감정 분석 컬럼 포함)
- `users_table.sql`: `users` 테이블 (로그인/회원가입용)
- `personal_test_results` 테이블: (개인 검사용)

**RLS는 전부 꺼둔 상태**로 운영 중. Supabase Auth가 아닌 자체 JWT 로그인 방식이라, 클라이언트가 Supabase를 직접 안 건드리고 항상 백엔드를 거쳐서만 DB에 접근함 → user_id 검증은 백엔드 코드가 전담.

## 담당

| 파일/폴더
| -------------------------------------------------------------
| `services/llama_service.py`, `models/llama_loader.py`
| `services/kobert_service.py`, `models/kobert_loader.py`
| `services/ad3_service.py`, `models/ad3_loader.py`
| `services/stats_service.py`
| `services/auth_service.py`, `repositories/user_repository.py`
| `routers/personal_test.py` 등 관련 파일
| DB 테이블 스키마 (Supabase)
| 나머지 (main, 나머지 schemas/routers/repositories)

## API 엔드포인트

### POST `/signup` — 회원가입

**Request**

```json
{
  "email": "test@example.com",
  "password": "test1234",
  "nickname": "테스트유저"
}
```

**Response**

```json
{
  "status": "success",
  "access_token": "eyJ...",
  "user_id": 1,
  "nickname": "테스트유저"
}
```

### POST `/login` — 로그인

**Request**

```json
{ "email": "test@example.com", "password": "test1234" }
```

**Response**: `/signup`과 동일한 형태

### POST `/generate-diary` — 일기 생성

**Request**

```json
{
  "what": "카페에서 과제 하기",
  "why": "시험기간이라 집중해서 공부하려고",
  "who": ["혼자"],
  "when": "주말 오후 2시",
  "where": "집 앞 카페",
  "user_id": "선택사항"
}
```

**Response**

```json
{
  "status": "success",
  "generated_diary": "주말 오후에...",
  "validation_failed": false
}
```

일기 생성 시 KoBERT 감정 분석도 같이 돌아가서, `top_emotion`/`emotion_scores`/`sentiment_score`까지 DB에 함께 저장됨.

### GET `/diaries/{user_id}` — 일기 목록 조회

### GET `/stats/daily/{user_id}?date=2026-08-03` — 일간 통계

**Response**

```json
{
  "date": "2026-08-03",
  "top_emotion": "편안한",
  "top3_emotions": [{"emotion": "편안한", "score": 0.6}, ...],
  "companions": ["친구", "연인"],
  "places": ["한강공원"]
}
```

### GET `/stats/monthly/{user_id}?year=2026&month=8` — 월간 통계

**Response**

```json
{
  "year": 2026, "month": 8,
  "top_emotion": "평온",
  "top3_emotions": [...],
  "emotion_flow": [{"date": "2026-08-01", "sentiment_score": 0.7, "top_emotion": "행복한"}, ...],
  "emotion_distribution": [{"emotion": "행복한", "percentage": 35.2, "color": "#E4A4C2", "valence": "긍정감정"}, ...],
  "most_positive_day": "2026-08-01",
  "most_negative_day": "2026-08-15",
  "top_companion": {"name": "친구", "count": 5, "top3_emotions": [...]},
  "top_place": {"name": "한강공원", "count": 3, "top3_emotions": [...]}
}
```

`emotion_distribution`의 `color`는 중분류 색상 팔레트를 24개 소분류에 자동으로 매핑한 값. `valence`는 해당 감정의 대분류(긍정감정/부정감정).
