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
```

- `MOCK_MODE=true`: 실제 AI 모델 없이 가짜 응답으로 API 테스트 가능 (로컬 개발용)
- `SUPABASE_URL` / `SUPABASE_KEY`: 재유한테 받은 값. 없어도 서버는 켜지고, DB 저장만 스킵됨
- `HF_TOKEN`: Hugging Face 토큰 (MOCK_MODE=false로 실제 모델 쓸 때만 필요)

## 서버 실행

```powershell
python -m uvicorn app.main:app --reload
```

`http://127.0.0.1:8000/docs` 에서 API 테스트 가능 (Swagger UI)

## 폴더 구조

```
app/
├── main.py            # FastAPI 진입점 (CORS 설정 포함)
├── config.py          # 환경변수 로딩
├── database.py        # Supabase 클라이언트 (키 없으면 자동으로 DB 스킵 모드)
├── schemas/            # API 요청/응답 형태
├── routers/             # 엔드포인트
├── services/             # AI 모델 비즈니스 로직
├── models/               # AI 모델 로더 (싱글톤)
└── repositories/          # DB 읽기/쓰기
```

## DB 스키마

`supabase_schema.sql` 참고 - 재유가 Supabase SQL Editor에서 그대로 실행하면 됨.

## 담당

| 파일/폴더                                               | 담당 |
| ------------------------------------------------------- | ---- |
| `services/llama_service.py`, `models/llama_loader.py`   | 준원 |
| `services/kobert_service.py`, `models/kobert_loader.py` | 준원 |
| `services/sd3_service.py`, `models/sd3_loader.py`       | 재유 |
| `db_models`(Supabase 테이블)                            | 재유 |
| 나머지 (main, schemas, routers, repositories)           | 준원 |

## API 엔드포인트

### POST `/generate-diary`

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
