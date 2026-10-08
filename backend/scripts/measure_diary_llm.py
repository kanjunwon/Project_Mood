"""
backend/scripts/measure_diary_llm.py
일기 생성 LLM 점검용 측정 스크립트 (속도 / 감정 진단 / 프롬프트 변형 전후 비교). uvicorn이 떠 있는 서버에서 한 번 실행.

[서버 작업 순서] 서버를 재유와 같이 쓰므로 시작 전에 시간 맞추기. 예상 시간은 아래 '예상 소요' 참고
  ※ 서버 파이썬 환경은 backend/venv (--system-site-packages). 터미널마다 source venv/bin/activate를 맨 먼저 하고,
    pip install은 반드시 venv 안에서만.
  0. cd /workspace/Project_Mood/backend && source venv/bin/activate
  1. uvicorn 종료: 띄워둔 터미널에서 Ctrl+C (다른 곳에서 떠 있으면 pkill -f "uvicorn app.main:app")
                  pgrep -af "uvicorn app.main:app"  -> 아무것도 안 나와야 함
  2. git status  -> "nothing to commit, working tree clean"인지 확인
                  (수정된 파일이 있으면 멈추고 누가 고친 건지 먼저 확인. 재유가 서버에서 직접 고친 걸 수 있음)
  3. git fetch origin && git checkout llm-diary-diagnosis && git pull
  4. .env 확인: grep -E "ENABLE_DEBUG_ENDPOINTS|HF_HUB_OFFLINE|HF_HOME|COMFYUI_URL" .env
                ENABLE_DEBUG_ENDPOINTS=true 가 없으면 추가 (측정 끝나면 지우기)
  5. uvicorn 시작 (모델 미리 로딩 때문에 "Application startup complete"까지 1~2분)
                PYTHONUNBUFFERED=1 python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1 | tee uvicorn_diary_log.txt
  6. (터미널 2) cd /workspace/Project_Mood/backend && source venv/bin/activate
                BENCH_USER_ID=<가중치 검사를 한 계정 id> python scripts/measure_diary_llm.py --image-every 3
     -> 시작하자마자 '시작 전 점검'을 출력함. [중단] 줄이 나오면 그 안내대로 고치고 다시 실행
  7. 결과: bench_results/diary_llm_<시각>.md / .json (단계마다 저장되어 중간에 끊겨도 남음)
     git add -f bench_results && git commit -m "일기 LLM 측정 결과" && git push
  8. 되돌리기: uvicorn 종료 -> git status 확인 -> git checkout main && git pull
               -> .env에서 ENABLE_DEBUG_ENDPOINTS 삭제 -> uvicorn 시작

[무엇을 재나]
  0) 워밍업 job 1개 (ComfyUI 첫 로딩 등, 집계 제외)
  1) 감정 진단: 고정 문장(감정 단어 있는/없는 쌍 포함)에 대해 KoBERT 원본 vs 가중치 적용 후 상위3 (LLM 안 씀, 수 초)
  2) base(현재 프롬프트) -> emotion_word(규칙 2번 변형) -> fewshot_no_mealtime(예시 식사시간대 제거)
     순서로 같은 입력 10개씩 job을 돌림. 변형은 한 번에 하나만 바뀜.
     측정 job은 기본적으로 DB에 저장 안 함 (--save-db로 켤 수 있음).
     이미지 생성/업로드는 --image-every N으로 조절: 각 변형의 1, N+1, 2N+1번째 입력에서만 생성
     (기본 1 = 전부 생성 = 실제 앱과 같은 전체 시간. 0 = 전부 생략). 변형마다 같은 입력에서 생성하므로 비교 가능.
     job 전체 시간(60초 목표)은 이미지를 만든 job으로만 집계하고, 일기+감정 시간은 전체 job으로 집계.
  BENCH_USER_ID 계정의 퍼스널 검사 가중치가 적용됨 (검사 안 한 계정이면 가중치 비교가 안 됨 -> 결과에 표시).

예상 소요 (추정: KV 캐시 적용 후 18tok/s 기준, 재시도가 많으면 더 김. 실측 아님):
  job 1개 = 일기+감정 15~30초 + 이미지(변환+ComfyUI+업로드) 20~30초
  --image-every 1 (기본, 31개 전부 이미지): 18~31분
  --image-every 3 (변형마다 4개씩 이미지):   10~20분
  --image-every 0 (이미지 없음):              8~16분
  여기에 재시작/pull 3~5분 추가. --budget-min(기본 40분)을 넘기면 남은 job은 건너뛰고 저장 후 종료.
옵션:
  --base-url URL       기본 http://127.0.0.1:8000 (Cloudflare 안 거침)
  --budget-min N       기본 40
  --variants a,b,c     기본 base,emotion_word,fewshot_no_mealtime
  --image-every N      기본 1 (전부 생성). 0이면 이미지 생성/업로드 전부 생략
  --save-db            측정 job도 DB에 저장
  --emotion-file PATH  감정 진단에 추가할 문장 (한 줄에 하나, 예: 실제로 '지루한'이 나온 일기)
"""
import argparse
import json
import os
import re
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(BACKEND_DIR / ".env")

import subprocess  # noqa: E402

import httpx  # noqa: E402

from app.emotion_taxonomy import get_valence  # noqa: E402
from app.services.auth_service import create_access_token  # noqa: E402

TARGET_JOB_SEC = 60
POLL_SEC = 2
JOB_TIMEOUT_SEC = 300

# 평가용 고정 입력 (앱이 보내는 형식 그대로: who는 쉼표 문자열, when은 "10월 2일 목요일 오후 6시")
CASES = [
    {"name": "시험+삼겹살+노래방", "what": "시험 끝나고 친구들이랑 삼겹살 먹고 노래방", "why": "기말고사가 끝나서 스트레스 풀려고",
     "who": "친구", "when": "10월 2일 목요일 오후 6시", "where": "학교 앞 고깃집이랑 노래방"},
    {"name": "친구 생일", "what": "친한 친구 생일 축하", "why": "오랜만에 다 같이 모여서 축하해주고 싶어서",
     "who": "친구", "when": "10월 3일 금요일 오후 7시", "where": "친구네 집"},
    {"name": "강아지 산책", "what": "강아지랑 공원 산책", "why": "날씨가 좋아서",
     "who": "강아지", "when": "10월 4일 토요일 오전 10시", "where": "동네 공원"},
    {"name": "조별과제", "what": "조별과제 회의", "why": "다음 주 발표 자료를 정리하려고",
     "who": "친구", "when": "10월 6일 월요일 오후 3시", "where": "학교 도서관 스터디룸"},
    {"name": "부모님 통화", "what": "부모님이랑 영상통화", "why": "요즘 연락을 못 드려서",
     "who": "엄마,아빠", "when": "10월 5일 일요일 오후 9시", "where": "자취방"},
    {"name": "헬스장 등록", "what": "헬스장 등록하고 첫 운동", "why": "체력이 너무 떨어진 것 같아서",
     "who": "혼자", "when": "10월 6일 월요일 오후 8시", "where": "동네 헬스장"},
    {"name": "동아리 여행", "what": "동아리 사람들이랑 1박 2일 여행", "why": "학기 중간에 다 같이 쉬려고",
     "who": "친구", "when": "10월 4일 토요일 오전 9시", "where": "강릉 바닷가"},
    {"name": "이사", "what": "자취방 이사", "why": "계약이 끝나서 학교 가까운 곳으로 옮기려고",
     "who": "가족", "when": "10월 5일 일요일 오전 11시", "where": "새 자취방"},
    {"name": "넷플릭스", "what": "넷플릭스로 드라마 몰아보기", "why": "주말이라 아무것도 안 하고 쉬고 싶어서",
     "who": "혼자", "when": "10월 4일 토요일 오후 2시", "where": "내 방"},
    {"name": "카페 과제", "what": "카페에서 과제", "why": "마감이 내일이라서",
     "who": "혼자", "when": "10월 7일 화요일 오후 4시", "where": "학교 앞 카페"},
]

# 감정 진단용 고정 문장. 같은 내용에 감정 단어가 있는/없는 쌍을 넣어서, 단어 하나가 KoBERT 결과를 바꾸는지 봄
EMOTION_TEXTS = [
    "친구들이랑 노래방에 갔다. 다 같이 소리 지르면서 불렀다. 재밌었다.",
    "친구들이랑 노래방에 갔다. 다 같이 소리 지르면서 불렀다.",
    "넷플릭스로 드라마를 몰아봤다. 하루 종일 누워서 봤다. 재밌었다.",
    "넷플릭스로 드라마를 몰아봤다. 하루 종일 누워서 봤다.",
    "조별과제 회의를 했다. 다들 의견이 달라서 시간이 오래 걸렸다. 답답했다.",
    "조별과제 회의를 했다. 다들 의견이 달라서 시간이 오래 걸렸다.",
    "헬스장 등록하고 처음 운동했다. 생각보다 힘들었는데 끝나고 나니까 뿌듯했다.",
    "헬스장 등록하고 처음 운동했다. 러닝머신 좀 뛰고 기구 몇 개 해봤다.",
    "시험 끝나고 고기 먹고 노래방까지 갔다. 오랜만에 실컷 놀아서 재밌었다.",
    "강아지랑 공원 한 바퀴 돌았다. 날씨가 좋아서 오래 걸었다.",
]

# 일기에 '명시적인' 감정 표현이 있는지 판단하는 사전 (어간 일치). 긴 표현부터 찾고 찾은 부분은 지움.
CUE_POSITIVE = ["나쁘지 않", "재미있", "재밌", "즐거", "즐겁", "신났", "신나", "행복", "기뻤", "기쁘", "설레", "설렜",
                "뿌듯", "후련", "상쾌", "개운", "편안", "편했", "감사", "고마", "좋았", "반가", "반갑", "웃겼"]
CUE_NEGATIVE = ["재미없", "좋지 않", "안 좋", "별로였", "지루", "심심", "답답", "피곤", "힘들", "지쳤", "지친", "짜증",
                "화났", "화가 났", "슬펐", "슬프", "우울", "외로", "불안", "걱정", "막막", "실망", "후회", "무서",
                "두려", "속상", "아쉬", "귀찮", "졸렸", "졸려"]
MARGIN_SPLIT = 0.10  # 원본 1등-2등 확률 차이가 이보다 작으면 '확률이 갈림'으로 표시

REASON_KEYS = ["길이", "문장수", "해요체", "금지 문구", "뻔한 마무리", "다행 중복", "관계 지어냄", "술 지어냄", "식사시간대 지어냄"]
INVENTION_KEYS = {"술": "술 지어냄", "시간대": "식사시간대 지어냄", "관계": "관계 지어냄"}


def detect_cues(text: str) -> list:
    remaining = text or ""
    found = []
    for stem in sorted(CUE_POSITIVE + CUE_NEGATIVE, key=len, reverse=True):
        if stem in remaining:
            found.append((stem, "긍정감정" if stem in CUE_POSITIVE else "부정감정"))
            remaining = remaining.replace(stem, " ")
    return found


def cue_valence(cues: list) -> str:
    vals = {v for _, v in cues}
    if not vals:
        return "없음"
    return vals.pop() if len(vals) == 1 else "혼합"


def classify(text: str, raw_top: list, weighted_top: list) -> dict:
    """raw_top/weighted_top: [[감정, 확률], ...] 확률 내림차순. 판단은 긍정/부정(정서가) 일치 여부로만 함."""
    cues = detect_cues(text)
    cv = cue_valence(cues)
    raw1, w1 = raw_top[0][0], weighted_top[0][0]
    raw_val, w_val = get_valence(raw1), get_valence(w1)
    margin = round(raw_top[0][1] - raw_top[1][1], 3) if len(raw_top) > 1 else None
    if cv in ("긍정감정", "부정감정"):
        if w_val == cv:
            verdict = "일치"
        elif raw_val == cv:
            verdict = "가중치가 뒤집음"
        else:
            verdict = "KoBERT 원본부터 틀림"
    else:
        verdict = f"단서 {cv}" + (" + 확률 갈림" if margin is not None and margin < MARGIN_SPLIT else "")
    return {"cues": [c for c, _ in cues], "cue_valence": cv, "raw_top1": raw1, "weighted_top1": w1,
            "top1_changed_by_weight": raw1 != w1, "raw_margin": margin, "verdict": verdict}


def reason_key(reason: str) -> str:
    for key in REASON_KEYS:
        if reason.startswith(key):
            return key
    return reason


def _top(scores: dict, n=3) -> list:
    return [[e, round(v, 4)] for e, v in sorted((scores or {}).items(), key=lambda x: -x[1])[:n]]


def _fmt_top(top: list) -> str:
    return ", ".join(f"{e} {v:.2f}" for e, v in top)


def _avg(values):
    values = [v for v in values if v is not None]
    return round(statistics.mean(values), 2) if values else None


class Bench:
    def __init__(self, base_url: str, budget_min: float, save_db: bool, image_every: int = 1):
        self.base_url = base_url.rstrip("/")
        self.image_every = image_every
        self.budget_sec = budget_min * 60
        self.deadline = time.time() + self.budget_sec
        self.save_db = save_db
        self.user_id = int(os.environ.get("BENCH_USER_ID", "0") or 0)
        self.headers = {"Authorization": f"Bearer {create_access_token(user_id=self.user_id)}"}
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = BACKEND_DIR / "bench_results"
        out.mkdir(exist_ok=True)
        self.json_path = out / f"diary_llm_{ts}.json"
        self.md_path = out / f"diary_llm_{ts}.md"
        self.data = {"started_at": ts, "user_id": self.user_id, "save_db": save_db, "image_every": image_every,
                     "preflight": None, "emotion": None, "jobs": [], "skipped": []}

    def time_left(self):
        return self.deadline - time.time()

    def save(self):
        self.json_path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.md_path.write_text(render_markdown(self.data), encoding="utf-8")

    def preflight(self) -> dict:
        """서버를 켠 직후 문제를 빨리 알기 위한 점검. 결과를 출력하고 data["preflight"]에 남김."""
        pf = {"stop": []}
        # 1) 이 스크립트가 있는 체크아웃의 git 상태
        pf["local_branch"] = _git("rev-parse", "--abbrev-ref", "HEAD")
        pf["local_commit"] = _git("log", "-1", "--format=%h %s")
        dirty = _git("status", "--porcelain")
        pf["local_dirty_files"] = len(dirty.splitlines()) if dirty else 0

        # 2) 서버가 실제로 띄운 코드 (/debug/info: ENABLE_DEBUG_ENDPOINTS가 켜져 있어야 응답)
        pf["env_enable_debug"] = os.environ.get("ENABLE_DEBUG_ENDPOINTS", "(.env에 없음)")
        info = {}
        try:
            r = httpx.get(f"{self.base_url}/debug/info", headers=self.headers, timeout=10)
            pf["server_debug_endpoints"] = r.status_code == 200
            if r.status_code == 200:
                info = r.json()
        except Exception as e:
            pf["server_debug_endpoints"] = False
            pf["stop"].append(f"서버({self.base_url}) 응답 없음: {e!r} -> uvicorn이 떠 있는지 확인")
        pf["server_git"] = info.get("server_git")
        pf["server_mock_mode"] = info.get("mock_mode")
        if not pf["server_debug_endpoints"] and not pf["stop"]:
            pf["stop"].append("/debug/info 404 -> .env에 ENABLE_DEBUG_ENDPOINTS=true 넣고 uvicorn 재시작 "
                              "(또는 서버가 llm-diary-diagnosis 브랜치 코드로 안 떠 있음)")
        server_commit = (pf["server_git"] or {}).get("commit")
        if server_commit and pf["local_commit"] and not pf["local_commit"].startswith(server_commit):
            pf["stop"].append(f"서버가 띄운 커밋({server_commit})과 지금 체크아웃({pf['local_commit'][:7]})이 다름 "
                              "-> git pull 후 uvicorn을 재시작 안 한 것")
        if pf["server_mock_mode"]:
            pf["stop"].append("서버가 MOCK_MODE=true -> 실제 모델 측정이 안 됨")

        # 3) BENCH_USER_ID와 퍼스널 검사
        pf["bench_user_id"] = self.user_id or None
        pf["personal_test_completed"] = None
        pf["weight_profile_applied"] = None
        if self.user_id:
            try:
                st = httpx.get(f"{self.base_url}/personal-test/status", headers=self.headers, timeout=10).json()
                pf["personal_test_completed"] = st.get("completed")
            except Exception as e:
                pf["personal_test_completed"] = f"조회 실패: {e!r}"
            if pf["server_debug_endpoints"]:
                try:
                    em = httpx.post(f"{self.base_url}/debug/emotion", json={"texts": []}, headers=self.headers,
                                    timeout=30).json()
                    pf["weight_profile_applied"] = em.get("weight_applied")
                except Exception as e:
                    pf["weight_profile_applied"] = f"조회 실패: {e!r}"

        # 4) ComfyUI
        comfy = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
        pf["comfyui_url"] = comfy
        try:
            pf["comfyui_ok"] = httpx.get(f"{comfy}/system_stats", timeout=5).status_code == 200
        except Exception:
            pf["comfyui_ok"] = False
        if not pf["comfyui_ok"] and self.image_every != 0:
            pf["stop"].append(f"ComfyUI({comfy}) 응답 없음 -> ComfyUI를 먼저 켜거나, 이미지 없이 재려면 --image-every 0")

        self.data["preflight"] = pf
        print(render_preflight(pf))
        return pf

    def emotion(self, texts):
        r = httpx.post(f"{self.base_url}/debug/emotion", json={"texts": texts}, headers=self.headers, timeout=120)
        r.raise_for_status()
        body = r.json()
        for item in body["items"]:
            item.update(classify(item["text"], item["raw_top"], item["weighted_top"]))
        self.data["emotion"] = body
        self.save()
        return body

    def job(self, variant: str, case: dict, record: bool = True, make_image: bool = True):
        body = {k: case[k] for k in ("what", "why", "who", "when", "where")}
        body.update(prompt_variant=None if variant == "base" else variant, save_db=self.save_db,
                    make_image=make_image)
        t0 = time.time()
        r = httpx.post(f"{self.base_url}/debug/diary-jobs", json=body, headers=self.headers, timeout=30)
        r.raise_for_status()
        job_id = r.json()["job_id"]
        while True:
            time.sleep(POLL_SEC)
            s = httpx.get(f"{self.base_url}/debug/diary-jobs/{job_id}", headers=self.headers, timeout=30).json()
            if s["status"] != "processing" or time.time() - t0 > JOB_TIMEOUT_SEC:
                break
        entry = summarize_job(variant, case["name"], s, round(time.time() - t0, 2))
        if record:
            self.data["jobs"].append(entry)
            self.save()
        print(f"  [{variant}] {case['name']}: {entry.get('job_total_sec')}초"
              f"{' (이미지 포함)' if entry.get('image_generated') else ' (이미지 생략)'}, 시도 {entry.get('attempts')}회"
              f"{' (폴백)' if entry.get('fallback') else ''}, 사유 {entry.get('reasons')}, "
              f"감정 {entry.get('raw_top1')} -> {entry.get('top_emotion')} ({entry.get('verdict')})")
        return entry


def summarize_job(variant: str, case_name: str, s: dict, client_sec: float) -> dict:
    diag = s.get("diag") or {}
    result = s.get("result") or {}
    details = diag.get("diary_attempt_details") or []
    entry = {
        "variant": variant, "case": case_name, "status": s.get("status"), "error": s.get("error"),
        "job_total_sec": diag.get("job_total_sec", client_sec), "client_sec": client_sec,
        "queue_wait_sec": diag.get("queue_wait_sec"),
        "diary_total_sec": diag.get("diary_total_sec"), "attempts": diag.get("diary_attempts"),
        "fallback": diag.get("diary_fallback"), "kobert_sec": diag.get("kobert_sec"),
        "image_prompt_sec": diag.get("image_prompt_sec"), "comfyui_sec": diag.get("comfyui_sec"),
        "upload_sec": diag.get("upload_sec"), "image_total_sec": diag.get("image_total_sec"),
        "tokens_per_sec": _avg([d.get("tokens_per_sec") for d in details]),
        "attempt_details": details,
        "reasons": [reason_key(r) for d in details for r in d.get("reasons", [])],
        "diary": result.get("generated_diary"), "top_emotion": result.get("top_emotion"),
        "weight_applied": diag.get("weight_applied"),
        "image_generated": not diag.get("image_skipped", False),
        "diary_emotion_sec": (round(diag["diary_total_sec"] + diag["kobert_sec"], 2)
                              if diag.get("diary_total_sec") is not None and diag.get("kobert_sec") is not None else None),
    }
    raw = diag.get("kobert_raw_scores")
    if raw and result.get("emotion_scores"):
        raw_top, w_top = _top(raw), _top(result["emotion_scores"])
        entry.update(raw_top=raw_top, weighted_top=w_top, raw_top1=raw_top[0][0])
        entry.update({k: v for k, v in classify(entry["diary"], raw_top, w_top).items()
                      if k in ("cues", "cue_valence", "verdict", "top1_changed_by_weight", "raw_margin")})
    return entry


def _git(*args):
    try:
        out = subprocess.run(["git", *args], cwd=BACKEND_DIR, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=10)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def image_for_index(i: int, image_every: int) -> bool:
    """변형 안에서 i번째(0부터) 입력에 이미지를 만들지. 0이면 전부 생략, 1이면 전부 생성."""
    return image_every > 0 and i % image_every == 0


def _image_rule(image_every: int) -> str:
    if image_every == 0:
        return "전부 생략"
    if image_every == 1:
        return "전부 생성"
    return f"각 변형의 1, {image_every + 1}, {2 * image_every + 1}...번째 입력에서만 생성"


def render_preflight(pf: dict) -> str:
    sg = pf.get("server_git") or {}

    def yn(v):
        return "O" if v is True else "X" if v is False else str(v)

    lines = [
        "===== 시작 전 점검 =====",
        f"- 이 체크아웃: 브랜치 {pf.get('local_branch')}, 커밋 {pf.get('local_commit')}, 수정된 파일 {pf.get('local_dirty_files')}개",
        f"- 서버가 띄운 코드: 브랜치 {sg.get('branch')}, 커밋 {sg.get('commit')}",
        f"- ENABLE_DEBUG_ENDPOINTS: .env 값 {pf.get('env_enable_debug')}, 서버 /debug 응답 {yn(pf.get('server_debug_endpoints'))}",
        f"- BENCH_USER_ID: {pf.get('bench_user_id') or '미설정 (user_id=0으로 실행, 가중치 비교 불가)'}"
        + (f", 퍼스널 검사 완료 {yn(pf.get('personal_test_completed'))}, 가중치 실제 적용 {yn(pf.get('weight_profile_applied'))}"
           if pf.get("bench_user_id") else ""),
        f"- ComfyUI({pf.get('comfyui_url')}): 응답 {yn(pf.get('comfyui_ok'))}",
    ]
    lines += [f"[중단] {msg}" for msg in pf.get("stop", [])]
    if pf.get("local_dirty_files"):
        lines.append("[주의] 체크아웃에 수정된 파일이 있음 -> git status로 확인")
    if pf.get("bench_user_id") and pf.get("personal_test_completed") is True and pf.get("weight_profile_applied") is False:
        lines.append("[주의] 퍼스널 검사는 했는데 가중치 프로필이 없음 -> 가중치 비교 불가 (원본=가중치 후)")
    return "\n".join(lines)


def render_markdown(data: dict) -> str:
    L = [f"# 일기 LLM 측정 ({data['started_at']})", "",
         f"- BENCH_USER_ID={data['user_id']}, DB 저장={'O' if data['save_db'] else 'X (측정 job은 저장 안 함)'}",
         f"- 목표: job 완료 {TARGET_JOB_SEC}초 이내",
         f"- 이미지 생성: --image-every {data.get('image_every', 1)} ({_image_rule(data.get('image_every', 1))})",
         ""]
    if data.get("preflight"):
        L += ["## 0. 시작 전 점검", "", "```", render_preflight(data["preflight"]), "```", ""]
    jobs = [j for j in data["jobs"] if j.get("status") == "done"]
    variants = list(dict.fromkeys(j["variant"] for j in data["jobs"]))

    # 1. 전후 비교 요약
    L += ["## 1. 변형별 요약 (같은 입력, 같은 조건)", "",
          "| 변형 | job 수 | job 전체 시간 평균/최대(초, 이미지 포함 job만) | 60초 초과 / 이미지 포함 job | "
          "일기+감정 시간 평균/최대(초, 전체 job) | 재시도 있는 job | 평균 시도 수 | 안전 템플릿 폴백 | "
          "지어내기 적발(술/시간대/관계, 전체 시도 기준) | 뻔한 마무리 적발 | 명시적 감정 단서 있는 최종 일기 | 감정 단서와 최종 감정 일치 | 생성 tok/s |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for v in variants:
        js = [j for j in jobs if j["variant"] == v]
        if not js:
            continue
        reasons = [r for j in js for r in j["reasons"]]
        inv = "/".join(str(reasons.count(k)) for k in INVENTION_KEYS.values())
        with_cue = [j for j in js if j.get("cue_valence") in ("긍정감정", "부정감정")]
        match = sum(1 for j in with_cue if j.get("verdict") == "일치")
        times = [j["job_total_sec"] for j in js if j.get("image_generated")]
        de = [j["diary_emotion_sec"] for j in js if j.get("diary_emotion_sec") is not None]
        full = f"{_avg(times)} / {max(times)}" if times else "- (이미지 생성 job 없음)"
        L.append(
            f"| {v} | {len(js)} | {full} | {sum(1 for t in times if t > TARGET_JOB_SEC)} / {len(times)} | "
            f"{_avg(de)} / {max(de) if de else None} | "
            f"{sum(1 for j in js if (j['attempts'] or 0) > 1)} | {_avg([j['attempts'] for j in js])} | "
            f"{sum(1 for j in js if j['fallback'])}/{len(js)} | {inv} | {reasons.count('뻔한 마무리')} | "
            f"{len(with_cue)}/{len(js)} | {match}/{len(with_cue)} | {_avg([j['tokens_per_sec'] for j in js])} |")
    L += ["", "지어내기/뻔한 마무리는 검증기가 걸러낸 횟수(불합격 시도 포함). 통과한 최종 일기에는 구조상 0건이고,"
          " '장면' 지어내기는 자동 판별이 안 돼서 아래 4번 표에서 사람이 판단.", ""]

    # 2. 단계별 시간
    L += ["## 2. 단계별 시간 (job별)", "",
          "| 변형 | 입력 | 이미지 | job 전체 | 대기 | 일기 생성 | 시도 수 | 불합격 사유 | KoBERT | 프롬프트 변환 | ComfyUI | 업로드 | tok/s |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for j in data["jobs"]:
        if j.get("status") != "done":
            L.append(f"| {j['variant']} | {j['case']} | - | 실패: {j.get('error')} |||||||||| ")
            continue
        L.append(f"| {j['variant']} | {j['case']} | {'O' if j.get('image_generated') else 'X'} | {j['job_total_sec']} | "
                 f"{j['queue_wait_sec']} | {j['diary_total_sec']} | "
                 f"{j['attempts']}{' (폴백)' if j['fallback'] else ''} | {', '.join(j['reasons']) or '-'} | {j['kobert_sec']} | "
                 f"{j['image_prompt_sec']} | {j['comfyui_sec']} | {j['upload_sec']} | {j['tokens_per_sec']} |")
    L.append("")

    # 3. 불합격 사유 집계
    L += ["## 3. 검증 불합격 사유 집계 (전체 시도 기준)", "", "| 사유 | " + " | ".join(variants) + " |",
          "|---|" + "---|" * len(variants)]
    for key in REASON_KEYS:
        L.append(f"| {key} | " + " | ".join(
            str(sum(j["reasons"].count(key) for j in jobs if j["variant"] == v)) for v in variants) + " |")
    L.append("")

    # 4. 감정 (생성된 일기)
    L += ["## 4. 생성된 일기와 감정 (사람 판단 칸: 감정이 맞는지 O/X, 장면 지어내기 여부)", "",
          "| 변형 | 입력 | 최종 일기 | 감정 단서 | KoBERT 원본 상위3 | 가중치 후 상위3 | 자동 분류 | 감정 O/X | 장면 지어냄 |",
          "|---|---|---|---|---|---|---|---|---|"]
    for j in jobs:
        diary = (j.get("diary") or "").replace("|", "/").replace("\n", " ")
        L.append(f"| {j['variant']} | {j['case']} | {diary} | {', '.join(j.get('cues') or []) or '없음'} | "
                 f"{_fmt_top(j.get('raw_top') or [])} | {_fmt_top(j.get('weighted_top') or [])} | {j.get('verdict')} |  |  |")
    L.append("")

    # 5. 감정 진단 (고정 문장)
    emo = data.get("emotion")
    if emo:
        L += ["## 5. 감정 진단 - 고정 문장 (LLM 없이 KoBERT/가중치만)", "",
              f"가중치 프로필 적용: {'O' if emo['weight_applied'] else 'X (이 계정은 퍼스널 검사 결과 없음 -> 원본=가중치 후)'}", "",
              "| 문장 | 감정 단서 | 원본 상위3 | 가중치 후 상위3 | 원본 1-2등 차 | 가중치로 1등 바뀜 | 분류 |",
              "|---|---|---|---|---|---|---|"]
        for it in emo["items"]:
            L.append(f"| {it['text']} | {', '.join(it['cues']) or '없음'} | {_fmt_top(it['raw_top'][:3])} | "
                     f"{_fmt_top(it['weighted_top'][:3])} | {it['raw_margin']} | {'O' if it['top1_changed_by_weight'] else 'X'} | {it['verdict']} |")
        L.append("")
    all_items = (emo["items"] if emo else []) + [j for j in jobs if j.get("verdict")]
    if all_items:
        counts = {}
        for it in all_items:
            counts[it["verdict"]] = counts.get(it["verdict"], 0) + 1
        L += ["### 감정 원인 분류 집계 (고정 문장 + 생성된 일기 전체)", "",
              "| 분류 | 건수 |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(counts.items(), key=lambda x: -x[1])]
        L += ["", "분류 기준 (정서가=긍정/부정 일치로만 판단):",
              "- 감정 단서: 일기에 명시적 감정 표현(사전: 재밌/답답/뿌듯/지루/피곤 등 어간)이 있는지. 긍정과 부정이 섞이면 '혼합'",
              "- 일치: 단서의 정서가 = 가중치 후 1등의 정서가",
              "- 가중치가 뒤집음: 원본 1등은 단서와 맞았는데 가중치 후 1등이 틀림",
              "- KoBERT 원본부터 틀림: 원본 1등부터 단서와 정서가가 다름",
              f"- 단서 없음/혼합: 판단 기준이 없음. 원본 1-2등 확률 차가 {MARGIN_SPLIT} 미만이면 '확률 갈림' 추가", ""]

    if data["skipped"]:
        L += ["## 건너뜀 (시간 예산 초과)", ""] + [f"- {s}" for s in data["skipped"]] + [""]
    return "\n".join(L) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--budget-min", type=float, default=40)
    parser.add_argument("--variants", default="base,emotion_word,fewshot_no_mealtime")
    parser.add_argument("--image-every", type=int, default=1)
    parser.add_argument("--save-db", action="store_true")
    parser.add_argument("--emotion-file")
    args = parser.parse_args()

    if args.image_every < 0:
        sys.exit("--image-every는 0 이상")
    bench = Bench(args.base_url, args.budget_min, args.save_db, args.image_every)
    print(f"결과 파일: {bench.md_path}")
    pf = bench.preflight()
    bench.save()
    if pf["stop"]:
        sys.exit("시작 전 점검에서 [중단] 항목이 있어 측정을 시작하지 않음")

    texts = list(EMOTION_TEXTS)
    if args.emotion_file:
        texts += [l.strip() for l in Path(args.emotion_file).read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"\n[1] 감정 진단 (고정 문장 {len(texts)}개)")
    emo = bench.emotion(texts)
    for it in emo["items"]:
        print(f"  {it['verdict']:<14} {_fmt_top(it['raw_top'][:3])}  ->  {_fmt_top(it['weighted_top'][:3])}  | {it['text'][:40]}")

    print("\n[warmup] job 1개 (집계 제외)")
    bench.job("base", CASES[0], record=False, make_image=args.image_every != 0)
    bench.deadline = time.time() + bench.budget_sec

    for variant in [v.strip() for v in args.variants.split(",") if v.strip()]:
        print(f"\n[{variant}] job {len(CASES)}개")
        for i, case in enumerate(CASES):
            if bench.time_left() < 90:
                bench.data["skipped"].append(f"{variant} / {case['name']}")
                continue
            bench.job(variant, case, make_image=image_for_index(i, args.image_every))

    bench.save()
    md = render_markdown(bench.data)
    print("\n" + "=" * 80)
    print(md.split("## 4.")[0])  # 표 1~3 (일기 전문/감정표는 파일에서)
    print(f"저장됨: {bench.md_path}\n        {bench.json_path}")


if __name__ == "__main__":
    main()
