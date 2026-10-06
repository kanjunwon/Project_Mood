# 일기/이미지 응답 분리 설계안 (초안, 코드 미반영)

측정 결과 이미지 프롬프트 변환을 줄여도 `/generate-diary` 전체가 Cloudflare 100초 제한에 가까우면 쓰는 대안.
**아직 app/ 코드에는 반영하지 않았음.** 아래 코드는 초안이고, 적용하려면 프론트 수정이 같이 필요함.

## 왜 "별도 엔드포인트로 이미지 요청"이 아니라 "백그라운드 생성 + 폴링"인가

| 방식 | 요청 1개의 최대 시간 | 100초 제한 |
|---|---|---|
| 지금 (한 요청에 전부) | 일기 + KoBERT + 변환 93.5 + ComfyUI 12 + 업로드 2.7 ≈ 108초 이상 | 넘음 |
| 이미지 전용 엔드포인트를 프론트가 따로 호출 | 변환 93.5 + ComfyUI 12 + 업로드 2.7 ≈ 108초 | **여전히 넘음** (변환을 줄이지 못하면 의미 없음) |
| 백그라운드 생성 + 상태 폴링 | 일기 응답: 일기 + KoBERT (몇십 초) / 폴링: 1초 미만 | 어떤 요청도 안 넘음 |

그래서 이미지 생성은 서버 안에서 응답을 보낸 뒤 이어서 돌리고, 프론트는 짧은 요청으로 상태만 물어보는 구조로 제안함.

## 흐름

```
POST /generate-diary
  1. 일기 생성 (LLM 1차) -> KoBERT -> 가중치 적용
  2. DB 저장 (image_url = null) -> diary_id 받음
  3. 응답 즉시 반환: 기존 필드 전부 + diary_id + image_status="pending" (image_url은 null)
  4. (응답 보낸 뒤) BackgroundTasks로 이미지 생성 -> 성공하면 diary_entries.image_url 업데이트

GET /diaries/{diary_id}/image   (프론트가 3초 간격으로 폴링, 최대 약 2분)
  -> {"status": "pending" | "done" | "failed", "image_url": "..." | null}
```

## 응답 스키마 호환성

- `DiaryResponse`에 **필드 추가만** 함: `diary_id: Optional[int]`, `image_status: Optional[str]`. 기존 필드 이름/타입은 그대로.
- 프론트(`DiaryApi.kt`의 `DiaryGenerateResponse`)는 Gson이라 모르는 필드는 무시함 -> **파싱은 안 깨짐.**
- 단, `image_url`이 항상 `null`로 옴. 지금 프론트는 `null`이면 감정별 일러스트로 대체하므로(`DiaryCompleteScreen.kt`의 `HeroImageWithTag`)
  **화면이 깨지지는 않지만, 완료 화면에서 생성된 그림이 안 보이게 됨.** 그림은 DB가 업데이트된 뒤 `/diaries/me`(캘린더 썸네일)에는 나옴.
  -> 완료 화면에서 그림을 보여주려면 프론트에 폴링을 추가해야 함 (아래).
- `test_diary.py`의 기존 테스트는 MOCK_MODE에서 이미지 생성을 안 하므로 그대로 통과할 것으로 예상 (확인 필요).

## 백엔드 코드 초안

### repositories/diary_repository.py

```python
def save_diary(data: dict):
    ...  # 기존 그대로 (response.data는 insert된 row 리스트라 id가 들어있음)


def update_diary_image(diary_id: int, image_url: str):
    if supabase is None:
        return None
    return supabase.table(TABLE_NAME).update({"image_url": image_url}).eq("id", diary_id).execute().data


def get_diary_image(diary_id: int, user_id: str):
    if supabase is None:
        return None
    rows = (supabase.table(TABLE_NAME).select("id, image_url")
            .eq("id", diary_id).eq("user_id", user_id).execute().data)
    return rows[0] if rows else None
```

### routers/diary.py

```python
from fastapi import BackgroundTasks
import threading

# 실패한 diary_id만 메모리에 기록 (서버 재시작하면 사라짐 -> 그땐 pending으로 보이다가 프론트 타임아웃)
# 정확히 하려면 diary_entries에 image_status 컬럼 추가 (alter table ... add column image_status text)
_IMAGE_FAILED: set[int] = set()

# LLM은 GPU 모델 하나를 공유함. 백그라운드 이미지 작업(LLM 2차 호출)과 다음 사람의 일기 생성(LLM 1차)이
# 동시에 model.generate()를 부르지 않도록 직렬화. (지금도 동시 요청이면 겹칠 수 있는 구조이긴 함)
LLM_LOCK = threading.Lock()   # llama_service._generate_once 안에서 with LLM_LOCK: 로 감싸는 걸 같이 적용


def _generate_image_job(diary_id, diary_text, top_emotion, request, profile):
    try:
        from app.services.sd3_service import generate_diary_image
        url = generate_diary_image(diary_text=diary_text, top_emotion=top_emotion, who=request.who,
                                   where=request.where, when=request.when, ...아바타/성별...)
        update_diary_image(diary_id, url)
    except Exception as e:
        print(f"[백그라운드] 이미지 생성 실패 diary_id={diary_id}: {e}")
        _IMAGE_FAILED.add(diary_id)


@router.post("/generate-diary", response_model=DiaryResponse)
def generate_diary(request: DiaryRequest, background_tasks: BackgroundTasks,
                   user_id: int = Depends(get_current_user_id)):
    ...  # 일기 생성, KoBERT, 가중치 - 기존 그대로
    saved = save_diary({... , "image_url": None})
    diary_id = saved[0]["id"] if saved else None

    image_status = None
    if not MOCK_MODE and diary_id is not None:
        background_tasks.add_task(_generate_image_job, diary_id, diary_text,
                                  emotion_result.get("top_emotion") or "편안한", request, profile)
        image_status = "pending"

    return DiaryResponse(..., image_url=None, diary_id=diary_id, image_status=image_status)


@router.get("/diaries/{diary_id}/image")
def get_diary_image_status(diary_id: int, user_id: int = Depends(get_current_user_id)):
    row = get_diary_image(diary_id, str(user_id))
    if row is None:
        raise HTTPException(status_code=404, detail="일기를 찾을 수 없음")
    if row.get("image_url"):
        return {"status": "done", "image_url": row["image_url"]}
    if diary_id in _IMAGE_FAILED:
        return {"status": "failed", "image_url": None}
    return {"status": "pending", "image_url": None}
```

### schemas/diary.py

```python
class DiaryResponse(BaseModel):
    ...  # 기존 필드 그대로
    diary_id: Optional[int] = None
    image_status: Optional[str] = None  # "pending" | None(MOCK_MODE/DB 없음)
```

## 프론트 변경 (필요한 것만)

1. `DiaryGenerateResponse`에 `diaryId: Long?`, `imageStatus: String?` 추가
2. `DiaryApi`에 `@GET("diaries/{id}/image") suspend fun getDiaryImage(@Path("id") id: Long): DiaryImageStatus`
3. `DiaryViewModel.submitDiary()` 성공 후 `imageStatus == "pending"`이면 3초 간격으로 최대 40번 폴링,
   `done`이면 `imageUrl`을 상태에 반영 -> 완료 화면이 감정 일러스트에서 생성 이미지로 바뀜
4. `ApiClient.kt`의 `readTimeout(240초)`는 그대로 둬도 되지만, 일기 응답이 빨라지므로 줄여도 됨

## 주의할 점

- `BackgroundTasks`는 같은 uvicorn 프로세스의 스레드풀에서 돌아감. 서버가 그 사이 재시작되면 작업이 사라짐
  (이 프로젝트 규모에선 감수 가능, 큐(Celery/RQ)까지는 과함).
- 백그라운드 작업이 GPU를 쓰는 동안 다음 사용자의 일기 생성이 같이 들어오면 둘 다 느려짐 -> `LLM_LOCK` 필요.
- `/diaries/me` 목록에는 이미지가 아직 없는 일기도 나옴 (image_url null) -> 캘린더는 이미 null을 처리하고 있음.
