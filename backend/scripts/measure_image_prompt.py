"""
backend/scripts/measure_image_prompt.py
이미지 프롬프트 변환 단계(LLM 2차 호출) 측정 스크립트. GPU 서버에서 uvicorn이 떠 있는 상태로 한 번 실행하면 끝.

[서버 켰을 때 순서] (서버비 시간당 약 $0.56 -> 전체 20~30분 안에 끝내기)
  ※ 서버 파이썬 환경은 backend/venv (--system-site-packages). 터미널마다 source venv/bin/activate를 맨 먼저 하고,
    pip install은 반드시 venv 안에서만 (시스템 환경에 깔다가 패키지 충돌 난 적 있음).
  1. RunPod Pod Start -> 웹 터미널 2개 열기
  2. (터미널 1) cd /workspace/<레포>/backend
                source venv/bin/activate        # 반드시 먼저
                git pull
                grep -v "^torch" requirements.txt > requirements_nogpu.txt && pip install -r requirements_nogpu.txt   # venv 안에서만
  3. (터미널 1) .env에 아래 한 줄 추가 (측정 끝나면 지우기):
                ENABLE_DEBUG_ENDPOINTS=true
  4. (터미널 1) ComfyUI가 안 떠 있으면 먼저 실행, 그다음
                PYTHONUNBUFFERED=1 python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1 | tee uvicorn_log.txt
  5. (터미널 2) cd /workspace/<레포>/backend
                source venv/bin/activate        # 터미널 2에서도 반드시 먼저
                BENCH_USER_ID=<내 테스트 계정 id> python scripts/measure_image_prompt.py
     - 워밍업(모델 로딩)은 스크립트가 알아서 먼저 하고 측정에서 뺌. 따로 워밍업 요청 안 보내도 됨.
     - BENCH_USER_ID를 주면 마지막에 /generate-diary 전체 파이프라인도 2번(워밍업 1 + 측정 1) 돌림.
       이때 그 계정에 일기 2개 + 이미지 2장이 실제로 저장됨. 안 주면 이 단계는 건너뜀.
  6. 결과: backend/bench_results/image_prompt_<시각>.md (사람용 요약) / .json (raw 출력 전문 포함)
     실행 중에도 단계마다 파일을 덮어써서, 중간에 끊겨도 그때까지 결과는 남음.
     /workspace는 Stop해도 유지됨. 가져오려면: git add -f bench_results && git commit && git push
     (uvicorn_log.txt에는 raw 출력/단계별 [TIMING] 로그 전문이 남음)
  7. 바로 Pod Stop (Terminate 금지)

예상 소요: 워밍업 1~3분 + 측정 약 12~16분. --budget-min(기본 18분)을 넘기면 남은 단계는 건너뛰고 저장 후 종료.
uvicorn에 직접 붙으므로(127.0.0.1:8000) Cloudflare 100초 제한과 무관.

옵션:
  --base-url URL     기본 http://127.0.0.1:8000
  --budget-min N     측정 시간 상한(분), 기본 18
  --quick            단일 변수 조합 단계를 건너뜀 (시간이 빠듯할 때)
"""
import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(BACKEND_DIR / ".env")

import httpx  # noqa: E402  (requests는 requirements.txt에 없어서 httpx 사용)

from app.services.auth_service import create_access_token  # noqa: E402

# 같은 입력을 모든 조합에 똑같이 넣음. diary_text는 실제 일기 생성 결과와 비슷한 문체로 작성.
CASES = [
    {
        "name": "정보 많음 (혼자, 카페 공부)",
        "diary_text": "주말 오후에 집 앞 카페로 노트북 들고 나갔다. 창가 자리가 비어 있어서 거기 앉아 아이스 아메리카노 "
                      "시켜놓고 밀린 과제를 했다. 처음엔 집중이 잘 안 됐는데 한 시간쯤 지나니까 손이 빨라졌다. "
                      "해 질 무렵에 마지막 문단까지 다 쓰고 저장 버튼을 눌렀다. 나오는 길에 바람이 시원했다.",
        "who": "혼자",
        "emotion": "뿌듯한",
        "where": "집 앞 카페",
        "when": "10월 4일 토요일 오후 2시",
        "gender": "여성",
    },
    {
        "name": "정보 적음 (가족, 본가)",
        "diary_text": "오랜만에 본가에 갔다. 엄마가 해준 밥 먹고 그냥 누워 있었다.",
        "who": "가족",
        "emotion": "편안한",
        "where": "본가",
        "when": "10월 5일 일요일 오후 1시",
        "gender": "남성",
    },
    {
        "name": "인원 많음 (친구들, 생일파티)",
        "diary_text": "친구 생일이라 저녁에 걔네 집으로 갔다. 동기들도 다 같이 모여서 케이크에 초 꽂고 노래 불러줬다. "
                      "다 같이 사진도 찍고 이런저런 얘기 하다 보니 시간 가는 줄 몰랐다.",
        "who": "친구,여성친구,남성친구",
        "emotion": "신나는",
        "where": "친구네 집",
        "when": "10월 2일 목요일 오후 7시",
        "gender": "여성",
    },
]
# template 방식만 추가로 확인할 케이스 (LLM 시간 안 씀)
TEMPLATE_ONLY_CASES = [
    {
        "name": "사람 많은 장소 (연인, 놀이공원)",
        "diary_text": "연인이랑 놀이공원에 가서 롤러코스터를 탔다. 사람이 엄청 많아서 줄이 길었다.",
        "who": "연인",
        "emotion": "설레는",
        "where": "놀이공원",
        "when": "10월 3일 금요일 오전 11시",
        "gender": "남성",
    },
]

COMBINED = {"do_sample": False, "stop_on_json_close": True, "num_examples": 3,
            "fixed_negative": True, "max_new_tokens": 120}

# (라벨, overrides) - 정보가 큰 순서대로. 시간이 모자라면 뒤에서부터 잘림.
SINGLE_FACTOR = [
    ("stop_on_json_close", {"stop_on_json_close": True}),
    ("greedy", {"do_sample": False}),
    ("fixed_negative", {"fixed_negative": True}),
    ("num_examples=2", {"num_examples": 2}),
    ("fixed_negative+max_new_tokens=120", {"fixed_negative": True, "max_new_tokens": 120}),
    ("max_new_tokens=150", {"max_new_tokens": 150}),
]

REQUEST_TIMEOUT = 400


class Bench:
    def __init__(self, base_url: str, budget_min: float):
        self.base_url = base_url.rstrip("/")
        self.deadline = time.time() + budget_min * 60
        self.user_id = int(os.environ.get("BENCH_USER_ID", "0") or 0)
        token = create_access_token(user_id=self.user_id)
        self.headers = {"Authorization": f"Bearer {token}"}
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.out_dir = BACKEND_DIR / "bench_results"
        self.out_dir.mkdir(exist_ok=True)
        self.json_path = self.out_dir / f"image_prompt_{ts}.json"
        self.md_path = self.out_dir / f"image_prompt_{ts}.md"
        self.data = {"started_at": ts, "base_url": self.base_url, "env": _image_prompt_env(),
                     "runs": [], "pipeline": [], "skipped": [], "model_info": None}

    def time_left(self) -> float:
        return self.deadline - time.time()

    def save(self):
        self.json_path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.md_path.write_text(render_markdown(self.data), encoding="utf-8")

    def image_prompt(self, case: dict, overrides: dict) -> dict:
        body = {k: case[k] for k in ("diary_text", "who", "emotion", "where", "when", "gender")}
        body["overrides"] = overrides
        t0 = time.time()
        resp = httpx.post(f"{self.base_url}/debug/image-prompt", json=body, headers=self.headers,
                             timeout=REQUEST_TIMEOUT)
        wall = time.time() - t0
        if resp.status_code == 404:
            sys.exit("/debug/image-prompt 가 404 -> .env에 ENABLE_DEBUG_ENDPOINTS=true 넣고 uvicorn 재시작 필요")
        resp.raise_for_status()
        report = resp.json()
        report["wall_sec"] = round(wall, 2)
        return report

    def run(self, phase: str, label: str, case: dict, overrides: dict):
        print(f"\n[{phase}] {label} / {case['name']} (남은 예산 {self.time_left() / 60:.1f}분)")
        try:
            report = self.image_prompt(case, overrides)
        except Exception as e:
            print(f"  실패: {e!r}")
            self.data["runs"].append({"phase": phase, "label": label, "case": case["name"],
                                      "overrides": overrides, "error": repr(e)})
            self.save()
            return None
        calls = report.get("calls", [])
        if report.get("model_info") and self.data["model_info"] is None:
            self.data["model_info"] = report["model_info"]
        print(f"  {report['total_sec']}초, LLM 호출 {len(calls)}회, fallback={report.get('fallback_used')}")
        for c in calls:
            print(f"    호출{c['attempt']}: 입력 {c.get('input_tokens')} / 생성 {c.get('output_tokens')}토큰"
                  f"{' (상한 도달)' if c.get('hit_max_new_tokens') else ''}, {c.get('elapsed_sec')}초, "
                  f"{c.get('tokens_per_sec')}tok/s, 파싱 {'OK' if c.get('parse_ok') else 'FAIL: ' + c.get('fail_reason', '')}")
        print(f"  positive: {report['positive']}")
        self.data["runs"].append({"phase": phase, "label": label, "case": case["name"],
                                  "overrides": overrides, **report})
        self.save()
        return report

    def pipeline(self, label: str):
        case = CASES[0]
        body = {"what": "카페에서 과제 하기", "why": "밀린 과제를 끝내려고", "who": case["who"],
                "when": case["when"], "where": case["where"]}
        print(f"\n[pipeline] {label} /generate-diary (남은 예산 {self.time_left() / 60:.1f}분)")
        t0 = time.time()
        try:
            resp = httpx.post(f"{self.base_url}/generate-diary", json=body, headers=self.headers,
                                 timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            wall = time.time() - t0
            timings = httpx.get(f"{self.base_url}/debug/last-pipeline-timings", headers=self.headers,
                                   timeout=30).json()
            entry = {"label": label, "wall_sec": round(wall, 2), "timings": timings,
                     "image_url": resp.json().get("image_url")}
        except Exception as e:
            entry = {"label": label, "error": repr(e)}
        print(f"  {json.dumps(entry, ensure_ascii=False)}")
        self.data["pipeline"].append(entry)
        self.save()


def _image_prompt_env() -> dict:
    return {k: v for k, v in os.environ.items() if k.startswith("IMAGE_PROMPT_")}


def _avg(values):
    values = [v for v in values if v is not None]
    return round(statistics.mean(values), 2) if values else None


TARGET_MAX_SEC = 40  # 목표: 변환 단계 30~40초대 -> 40초 이하면 달성
SIMILAR_JACCARD = 0.5  # "현재와 비슷한 품질" 판정에 쓰는 태그 겹침 비율 하한 (기계적 기준, 최종 판단은 눈으로)


def _tags(positive: str) -> list[str]:
    return [t.strip().lower() for t in (positive or "").split(",") if t.strip()]


def _people_tags(positive: str) -> list[str]:
    # 인원/관계 태그만 (1girl, 2boys, solo, couple) - 인원수가 바뀌면 그림이 완전히 달라지므로 따로 비교
    import re
    return sorted(t for t in _tags(positive) if re.fullmatch(r"\d+(girl|boy)s?", t) or t in ("solo", "couple"))


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(_tags(a)), set(_tags(b))
    return round(len(sa & sb) / len(sa | sb), 2) if sa | sb else 1.0


def render_summary(data: dict) -> str:
    """측정 결과 해석용 요약표 (스크립트 출력 맨 마지막 + .md 맨 위)"""
    runs = [r for r in data["runs"] if "error" not in r]
    baseline_by_case = {r["case"]: r for r in runs if r["phase"] == "baseline"}
    lines = ["## 해석용 요약", ""]

    # 1) 현재 설정 기준
    lines += ["### 1. 현재 설정(baseline) 기준", "",
              "| 케이스 | 변환 시간(초) | LLM 호출 수 | 재시도 | 입력 토큰 | 생성 토큰 (상한 도달 *) | tok/s | 파싱 실패 | fallback |",
              "|---|---|---|---|---|---|---|---|---|"]
    for case, r in baseline_by_case.items():
        calls = r.get("calls", [])
        lines.append(
            f"| {case} | {r['total_sec']} | {len(calls)} | {'O' if len(calls) > 1 else 'X'} | "
            f"{' / '.join(str(c.get('input_tokens')) for c in calls)} | "
            f"{' / '.join(str(c.get('output_tokens')) + ('*' if c.get('hit_max_new_tokens') else '') for c in calls)} | "
            f"{' / '.join(str(c.get('tokens_per_sec')) for c in calls)} | "
            f"{sum(1 for c in calls if not c.get('parse_ok'))} | {'O' if r.get('fallback_used') else 'X'} |"
        )
    if not baseline_by_case:
        lines.append("| (baseline 결과 없음) |||||||||")
    lines += ["", "호출이 여러 개면 ' / '로 구분 (첫 시도 / 재시도).", ""]

    # 2) 조합별 목표 달성
    groups = {}
    for r in runs:
        groups.setdefault((r["phase"], r["label"]), []).append(r)
    lines += [f"### 2. 조합별 목표 달성 (기준: 측정한 모든 케이스가 {TARGET_MAX_SEC}초 이하 + fallback 없음)", "",
              "| 단계 | 조합 | 케이스 수 | 평균(초) | 최대(초) | fallback | 목표 |", "|---|---|---|---|---|---|---|"]
    for (phase, label), rs in groups.items():
        worst = max(r["total_sec"] for r in rs)
        fallbacks = sum(1 for r in rs if r.get("fallback_used"))
        ok = worst <= TARGET_MAX_SEC and fallbacks == 0
        lines.append(f"| {phase} | {label} | {len(rs)} | {_avg([r['total_sec'] for r in rs])} | {worst} | "
                     f"{fallbacks}/{len(rs)} | {'O' if ok else 'X'} |")
    lines += ["", "single 단계는 '정보 많음' 케이스 1개만 측정한 값.", ""]

    # 3) template vs llm
    lines += ["### 3. template 모드", "",
              "| 케이스 | template 시간(초) | baseline(llm) positive에 있는데 template에 없는 태그 |", "|---|---|---|"]
    for r in runs:
        if r["phase"] != "template":
            continue
        base = baseline_by_case.get(r["case"])
        if base is None or base.get("fallback_used"):
            missing = "(비교할 baseline 결과 없음)"
        else:
            template_tags = set(_tags(r["positive"]))
            missing = ", ".join(t for t in _tags(base["positive"]) if t not in template_tags) or "(없음)"
        lines.append(f"| {r['case']} | {r['total_sec']} | {missing} |")
    lines += ["", "태그 문자열이 정확히 같은지로만 비교함 (예: 'smiling' vs 'smile'은 다른 태그로 셈).", ""]

    # 4) 가장 빠른 llm 조합 3개 + 품질 유사도
    candidates = []
    for (phase, label), rs in groups.items():
        if phase in ("baseline", "template"):
            continue
        sims, people_same, compared = [], 0, 0
        for r in rs:
            base = baseline_by_case.get(r["case"])
            if base is None or base.get("fallback_used"):
                continue
            compared += 1
            sims.append(_jaccard(r["positive"], base["positive"]))
            people_same += _people_tags(r["positive"]) == _people_tags(base["positive"])
        fallbacks = sum(1 for r in rs if r.get("fallback_used"))
        similar = (compared > 0 and fallbacks == 0 and people_same == compared
                   and (_avg(sims) or 0) >= SIMILAR_JACCARD)
        candidates.append({"phase": phase, "label": label, "avg": _avg([r["total_sec"] for r in rs]),
                           "n": len(rs), "jaccard": _avg(sims), "people": f"{people_same}/{compared}",
                           "fallbacks": fallbacks, "similar": similar})
    candidates.sort(key=lambda c: c["avg"])
    top3 = candidates[:3]
    lines += ["### 4. 가장 빠른 llm 조합 3개 (template 제외)", "",
              f"품질 '비슷' 기준: fallback 없음 + 인원 태그(1girl/2boys/solo/couple)가 baseline과 전부 일치 + "
              f"태그 겹침(Jaccard) 평균 {SIMILAR_JACCARD} 이상. baseline도 샘플링이라 매번 달라지므로 참고용.", "",
              "| 순위 | 단계 | 조합 | 케이스 수 | 평균(초) | 태그 겹침 | 인원 태그 일치 | fallback | 품질 비슷 |",
              "|---|---|---|---|---|---|---|---|---|"]
    for i, c in enumerate(top3, start=1):
        lines.append(f"| {i} | {c['phase']} | {c['label']} | {c['n']} | {c['avg']} | {c['jaccard']} | {c['people']} | "
                     f"{c['fallbacks']}/{c['n']} | {'O' if c['similar'] else 'X'} |")
    if not top3:
        lines.append("| - | (llm 조합 결과 없음) ||||||||")
    best = next((c for c in top3 if c["similar"]), None)
    lines.append("")
    if best:
        lines.append(f"-> 가장 빠른 3개 중 품질이 현재와 비슷한 조합: **{best['label']}** ({best['phase']}, 평균 {best['avg']}초)")
    else:
        lines.append("-> 가장 빠른 3개 중 기준을 만족하는 조합 없음 (.md의 '케이스별 positive 비교'를 눈으로 확인)")
    lines.append("")
    return "\n".join(lines) + "\n"


def render_markdown(data: dict) -> str:
    lines = [f"# 이미지 프롬프트 변환 측정 ({data['started_at']})", "", render_summary(data)]
    if data["env"]:
        lines += [f"서버 .env의 IMAGE_PROMPT_* 값: `{data['env']}` (overrides가 없는 항목은 이 값 기준)", ""]
    if data.get("model_info"):
        lines += ["## 모델 상태", "", "```", json.dumps(data["model_info"], ensure_ascii=False, indent=2), "```", ""]

    runs = [r for r in data["runs"] if "error" not in r]
    lines += ["## 조합별 요약", "",
              "| 단계 | 조합 | 케이스 수 | 평균 소요(초) | 최대(초) | 평균 LLM 호출 수 | 평균 입력 토큰 | 평균 생성 토큰 | 상한 도달 호출 | 파싱 실패 호출 | fallback | 평균 tok/s |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    groups = {}
    for r in runs:
        groups.setdefault((r["phase"], r["label"]), []).append(r)
    for (phase, label), rs in groups.items():
        calls = [c for r in rs for c in r.get("calls", [])]
        lines.append(
            f"| {phase} | {label} | {len(rs)} | {_avg([r['total_sec'] for r in rs])} | "
            f"{max(r['total_sec'] for r in rs)} | {_avg([len(r.get('calls', [])) for r in rs])} | "
            f"{_avg([c.get('input_tokens') for c in calls])} | {_avg([c.get('output_tokens') for c in calls])} | "
            f"{sum(1 for c in calls if c.get('hit_max_new_tokens'))}/{len(calls)} | "
            f"{sum(1 for c in calls if not c.get('parse_ok'))}/{len(calls)} | "
            f"{sum(1 for r in rs if r.get('fallback_used'))}/{len(rs)} | {_avg([c.get('tokens_per_sec') for c in calls])} |"
        )
    lines.append("")

    lines += ["## 케이스별 positive 비교", ""]
    for case_name in dict.fromkeys(r["case"] for r in runs):
        lines += [f"### {case_name}", ""]
        for r in runs:
            if r["case"] == case_name:
                lines.append(f"- **{r['phase']} / {r['label']}** ({r['total_sec']}초): `{r['positive']}`")
        lines.append("")

    lines += ["## 호출별 raw 출력 (baseline)", ""]
    for r in runs:
        if r["phase"] != "baseline":
            continue
        for c in r.get("calls", []):
            lines += [f"### {r['case']} / 호출 {c['attempt']} (생성 {c.get('output_tokens')}토큰, {c.get('elapsed_sec')}초, "
                      f"파싱 {'OK' if c.get('parse_ok') else 'FAIL: ' + c.get('fail_reason', '')})",
                      "", "```", c.get("raw_full", c.get("raw", "")), "```", ""]

    if data["pipeline"]:
        lines += ["## /generate-diary 전체 파이프라인", "", "```",
                  json.dumps(data["pipeline"], ensure_ascii=False, indent=2), "```", ""]
    errors = [r for r in data["runs"] if "error" in r]
    if errors or data["skipped"]:
        lines += ["## 실패/건너뜀", ""]
        lines += [f"- 실패: {r['phase']} / {r['label']} / {r['case']}: {r['error']}" for r in errors]
        lines += [f"- 건너뜀(시간 예산 초과): {s}" for s in data["skipped"]]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--budget-min", type=float, default=18)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()

    bench = Bench(args.base_url, args.budget_min)
    print(f"결과 파일: {bench.md_path}")

    httpx.get(f"{bench.base_url}/", timeout=10).raise_for_status()

    # 0) 워밍업: 모델 로딩 (측정에서 제외). 생성 토큰을 최소로 해서 빨리 끝냄
    print("\n[warmup] LLM 로딩 (첫 실행이면 몇 분 걸림, 측정 제외)")
    t0 = time.time()
    bench.image_prompt(CASES[0], {"mode": "llm", "max_new_tokens": 8, "max_attempts": 1})
    print(f"  워밍업 {time.time() - t0:.1f}초")
    bench.deadline = time.time() + args.budget_min * 60  # 예산은 워밍업 이후부터

    # 1) baseline: 현재 기본 설정 그대로 (병목 진단용 - 재시도인지, 과다 생성인지, 입력 길이인지)
    #    서버 .env에 IMAGE_PROMPT_*가 있으면 그 값이 섞이므로, 기본값을 명시적으로 넣음
    baseline = {"mode": "llm", "max_new_tokens": 200, "do_sample": True, "temperature": 0.3,
                "num_examples": 5, "stop_on_json_close": False, "fixed_negative": False, "max_attempts": 2}
    for case in CASES:
        bench.run("baseline", "현재 설정", case, baseline)

    # 2) template: LLM 호출 없음
    for case in CASES + TEMPLATE_ONLY_CASES:
        bench.run("template", "template", case, {"mode": "template"})

    # 3) 후보 전부 적용한 조합 - 목표(30~40초) 달성 가능한지 + 품질 비교용으로 전 케이스
    combined = {**baseline, **COMBINED}
    label = "greedy+stop+예시3+고정negative+max120"
    for case in CASES:
        if bench.time_left() < 120:
            bench.data["skipped"].append(f"combined / {case['name']}")
            continue
        bench.run("combined", label, case, combined)

    # 4) 단일 변수: 어떤 설정이 얼마나 줄이는지 (정보 많은 케이스 1개로만)
    if not args.quick:
        for label, overrides in SINGLE_FACTOR:
            if bench.time_left() < 120:
                bench.data["skipped"].append(f"single / {label}")
                continue
            bench.run("single", label, CASES[0], {**baseline, **overrides})

    # 5) 전체 파이프라인 단계별 시간 (현재 서버 .env 설정 기준)
    if bench.user_id:
        if bench.time_left() < 300:
            bench.data["skipped"].append("pipeline (/generate-diary)")
        else:
            bench.pipeline("warmup (KoBERT/ComfyUI 첫 로딩 포함, 참고용)")
            bench.pipeline("measured")
    else:
        bench.data["skipped"].append("pipeline (BENCH_USER_ID 미지정)")

    bench.save()
    print("\n" + "=" * 80)
    summary = render_summary(bench.data)
    details = render_markdown(bench.data).replace(summary, "")
    # raw 출력 전문은 길어서 터미널에는 안 찍음 (파일에는 있음). 그 뒤 섹션(파이프라인/실패)은 출력
    before_raw, _, after_raw = details.partition("## 호출별 raw 출력")
    tail = after_raw[min((i for i in (after_raw.find("## /generate-diary"), after_raw.find("## 실패/건너뜀")) if i >= 0),
                         default=len(after_raw)):]
    print(before_raw + tail)
    print(f"저장됨: {bench.md_path}\n        {bench.json_path}")
    print("\n" + "=" * 80)
    print(summary)  # 해석용 요약표는 맨 마지막에


if __name__ == "__main__":
    main()
