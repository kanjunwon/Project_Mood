"""
app/services/image_prompt_service.py
재유 스펙(핸드오프 문서) 그대로 구현.

파이프라인: 일기 생성(LLM 1번째 호출) -> 감정분석(KoBERT) -> 이미지 프롬프트 변환(LLM 2번째 호출) -> ComfyUI

기존 일기 생성용 LLaMA를 그대로 재사용함 (별도 모델 불필요, _generate_once 그대로 씀).

[.env 설정] 변환 단계가 너무 오래 걸려서(A6000 기준 93.5초) 코드 수정 없이 조합을 바꿔가며
측정할 수 있게 환경변수로 뺐음. 아무것도 안 주면 기존 동작과 완전히 같음.
  IMAGE_PROMPT_MODE=llm|template       (기본 llm) template이면 LLM 호출 없이 사전 매핑으로 변환
  IMAGE_PROMPT_MAX_NEW_TOKENS=200      (기본 200)
  IMAGE_PROMPT_DO_SAMPLE=true          (기본 true) false면 greedy, temperature/top_p 무시
  IMAGE_PROMPT_TEMPERATURE=0.3         (기본 0.3)
  IMAGE_PROMPT_NUM_EXAMPLES=5          (기본 5, 1~5) 줄일 때 남는 순서: 1인 -> 친구들 -> 놀이공원 -> 부모님 -> 대가족
  IMAGE_PROMPT_STOP_ON_JSON_CLOSE=false (기본 false) true면 JSON이 닫히는 순간 생성 중단
  IMAGE_PROMPT_FIXED_NEGATIVE=false    (기본 false) true면 LLM은 positive만 만들고 negative는 고정값 사용
                                        (negative는 매번 똑같은 긴 문자열이라 LLM이 다시 받아쓸 이유가 없음)
  IMAGE_PROMPT_MAX_ATTEMPTS=2          (기본 2) JSON 파싱 실패 시 총 시도 횟수
"""
import json
import os
import re
import time

# 예시/본문에 공통으로 들어가는 negative (v3, 인원수 초과 방지 항목 추가된 최신본)
FALLBACK_NEGATIVE = (
    "bad anatomy, extra limbs, missing limbs, deformed arm, malformed hands, "
    "extra fingers, missing fingers, fused fingers, mutated hands, disfigured, "
    "distorted, blurry, low quality, photorealistic, realistic, photo, 3d render, "
    "text, watermark, gibberish text, chinese text, chinese characters, kanji, hanzi, hanja, "
    "extra people, extra person, additional people, crowd, too many people, "
    "duplicate character, clone, multiple views, split screen"
)

_RULES = """당신은 한국어 일기를 Stable Diffusion(Illustrious XL) 이미지 생성용 영어 danbooru 태그 프롬프트로 변환하는 전문가입니다.

[입력으로 주어지는 것]
- 일기 본문 (한국어)
- 감정 라벨 (KoBERT 분석 결과)
- Who, What, When, Where 메타데이터

[출력 규칙]
1. 반드시 영어 danbooru 태그 형식으로 출력하세요. 자연어 문장이 아니라 쉼표로 구분된 태그 나열입니다.
2. 모든 태그 끝에는 반드시 "gamjeong style"을 붙이세요.

3. 인원수 규칙 (중요 — 반드시 정확한 숫자로 명시할 것):
   - "multiple people", "multiple girls", "multiple boys", "group of people" 같은 상한 없는 표현은 절대 사용 금지.
   - 1명: "1girl, solo" 또는 "1boy, solo"
   - 커플: "1girl, young adult woman, 1boy, young adult man, couple" (나이대와 관계 반드시 명시. "1girl, 1boy"만 쓰면 엄마+아들처럼 오인될 수 있음)
   - 2~6명(친구/동료/가족 등): 반드시 성별+정확한 숫자로 명시. 예: "3girls, 2boys", "2girls, 1boy"
   - 인원 태그는 프롬프트의 맨 앞부분에 배치하세요 (danbooru 계열 모델은 앞쪽 태그의 영향력이 더 큼).
   - 일기에 "친구들", "가족들", "동기들"처럼 정확한 인원수가 특정되지 않은 경우에도, 문맥상 합리적인 숫자를 추정해서 성별+숫자로 명시하되 절대 6명을 넘기지 마세요.
   - 실제 일기 내용상 인원이 6명을 초과하는 경우(예: 반 전체, 대가족 모임, 큰 파티)에도 이미지에는 최대 6명까지만 반영하고, 나머지 인원은 언급하지 않습니다.

4. 배경에 사람이 많은 장소 규칙 (놀이공원, 워터파크, 축제, 콘서트, 대형 행사장 등):
   - 전경(foreground)에 얼굴이 명확히 그려지는 인물은 최대 2~3명으로 제한: 성별+숫자 명시 (예: "2girls")
   - 배경 군중은 얼굴을 그리게 하는 표현을 쓰지 말고, "out of focus background", "bokeh", "blurred crowd silhouettes" 같은 표현만 사용
   - 배경 군중에 대해 "multiple people in background"처럼 사람 숫자나 사람이라는 개념을 구체화하는 표현은 쓰지 마세요.

5. 부모님/중장년층 등장 시 "mature female, mother" 또는 "mature male, father"를 반드시 포함하세요.

6. 감정 라벨에 따라 표정/분위기 태그를 추가하세요:
   - 긍정 감정: "smile, blush, warm lighting"
   - 부정 감정: "frown, tired expression, dim lighting" 등

7. 장소, 시간대, 소품은 일기 내용에서 구체적으로 추출해서 포함하세요.

8. 화풍 강조 태그("flat color, cel shading, line art, illustration")는 인원수가 4명 이상이거나 2인 이상 정면 구도일 때 반드시 추가하세요.

[출력 형식 - 반드시 이 JSON 형식으로만 답하세요]
"""

_FORMAT_FULL = (
    "{\n"
    '  "positive": "여기에 영어 태그 프롬프트",\n'
    f'  "negative": "{FALLBACK_NEGATIVE}"\n'
    "}"
)
_FORMAT_POSITIVE_ONLY = (
    "{\n"
    '  "positive": "여기에 영어 태그 프롬프트"\n'
    "}"
)

# (제목, 입력, positive) - 원래 순서 그대로. negative는 전부 FALLBACK_NEGATIVE와 동일했음.
_EXAMPLES = [
    ("1인",
     '일기="퇴근 후 지쳐서 집에 왔는데 고양이가 골골송을 부르며 반겨줬다", Who=["반려동물","고양이"], 감정="힐링됨"',
     "1girl, young adult woman, solo, cat, cuddling, sitting, living room, evening, warm indoor lighting, relieved expression, gamjeong style"),
    ("부모님",
     '일기="아빠와 함께 셀프 세차장에서 고압수 세차를 했다", Who=["가족","아빠"], 감정="흐뭇함"',
     "1boy, young adult man, mature male, father, high pressure water gun, washing car, self car wash, morning, casual clothes, smiling, gamjeong style"),
    ('인원수 특정 안 된 "친구들" (6명 상한 적용)',
     '일기="동아리 뒤풀이로 친구들이랑 노래방에 갔다", Who=["친구"], 감정="신남"',
     "3girls, 3boys, young adults, karaoke room, holding microphones, singing, colorful lighting, laughing, flat color, cel shading, line art, illustration, gamjeong style"),
    ("사람 많은 장소 (전경/배경 분리)",
     '일기="친구들이랑 놀이공원에 가서 롤러코스터를 탔다", Who=["친구"], 감정="신남"',
     "2girls, foreground, riding roller coaster, amusement park, screaming, excited expression, blurred crowd silhouettes in background, bokeh, sunny day, gamjeong style"),
    ("대가족 모임 (6명 초과 케이스, 대표인물+사물로 축소)",
     '일기="외할머니 칠순 잔치에 온 가족과 친척들이 모였다", Who=["가족","엄마","아빠","형제,자매"], 감정="행복함"',
     "1girl, young adult woman, elderly woman, grandmother, sitting together at table, birthday cake, candles, banquet table with many dishes, paper decorations, warm celebratory lighting, gamjeong style"),
]

# 예시를 줄일 때 남기는 우선순위 (0부터 인덱스): 1인 -> 친구들(인원 추정) -> 놀이공원(군중) -> 부모님 -> 대가족
_EXAMPLE_PRIORITY = [0, 2, 3, 1, 4]


def build_system_prompt(num_examples: int = 5, fixed_negative: bool = False) -> str:
    num_examples = max(0, min(num_examples, len(_EXAMPLES)))
    chosen = sorted(_EXAMPLE_PRIORITY[:num_examples])

    parts = [_RULES + (_FORMAT_POSITIVE_ONLY if fixed_negative else _FORMAT_FULL)]
    for no, idx in enumerate(chosen, start=1):
        title, user_input, positive = _EXAMPLES[idx]
        if fixed_negative:
            output = json.dumps({"positive": positive}, ensure_ascii=False)
        else:
            output = json.dumps({"positive": positive, "negative": FALLBACK_NEGATIVE}, ensure_ascii=False)
        parts.append(f"[예시 {no}] - {title}\n입력: {user_input}\n출력: {output}")
    return "\n\n".join(parts)


# 기본 설정(예시 5개, negative도 LLM이 출력)일 때의 프롬프트 = 분리 전 원본과 글자 하나까지 동일
# (test_image_prompt_service.py에서 원본 해시로 검증함)
SYSTEM_PROMPT = build_system_prompt()

JSON_PATTERN = re.compile(r'\{.*"positive"\s*:.*"negative"\s*:.*\}', re.DOTALL)
JSON_PATTERN_POSITIVE_ONLY = re.compile(r'\{.*"positive"\s*:.*\}', re.DOTALL)

# JSON이 닫히는 모양들 (한 줄짜리 예시 형식 / 여러 줄 형식 둘 다)
JSON_CLOSE_STOP_STRINGS = ['"}', '"\n}', '" }']

_DEFAULT_CONFIG = {
    "mode": "llm",
    "max_new_tokens": 200,
    "do_sample": True,
    "temperature": 0.3,
    "num_examples": 5,
    "stop_on_json_close": False,
    "fixed_negative": False,
    "max_attempts": 2,
}

_ENV_KEYS = {
    "mode": ("IMAGE_PROMPT_MODE", str),
    "max_new_tokens": ("IMAGE_PROMPT_MAX_NEW_TOKENS", int),
    "do_sample": ("IMAGE_PROMPT_DO_SAMPLE", "bool"),
    "temperature": ("IMAGE_PROMPT_TEMPERATURE", float),
    "num_examples": ("IMAGE_PROMPT_NUM_EXAMPLES", int),
    "stop_on_json_close": ("IMAGE_PROMPT_STOP_ON_JSON_CLOSE", "bool"),
    "fixed_negative": ("IMAGE_PROMPT_FIXED_NEGATIVE", "bool"),
    "max_attempts": ("IMAGE_PROMPT_MAX_ATTEMPTS", int),
}


def _cast(value, kind):
    if kind == "bool":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("1", "true", "yes", "on")
    return kind(value)


def get_config(overrides: dict | None = None) -> dict:
    """
    기본값 <- .env(환경변수) <- overrides 순서로 덮어씀.
    매 호출마다 환경변수를 다시 읽으니, 측정 스크립트처럼 값만 바꿔서 연달아 돌릴 수 있음.
    """
    cfg = dict(_DEFAULT_CONFIG)
    for key, (env_name, kind) in _ENV_KEYS.items():
        raw = os.environ.get(env_name)
        if raw is not None and raw.strip() != "":
            cfg[key] = _cast(raw, kind)
    for key, value in (overrides or {}).items():
        if key not in _ENV_KEYS:
            raise ValueError(f"알 수 없는 이미지 프롬프트 설정: {key}")
        cfg[key] = _cast(value, _ENV_KEYS[key][1])

    cfg["mode"] = str(cfg["mode"]).strip().lower()
    if cfg["mode"] not in ("llm", "template"):
        raise ValueError(f"IMAGE_PROMPT_MODE는 llm 또는 template만 가능: {cfg['mode']}")
    cfg["max_attempts"] = max(1, cfg["max_attempts"])
    return cfg


def _build_translation_prompt(diary_text: str, who, emotion: str, where: str, when: str,
                              system_prompt: str = SYSTEM_PROMPT) -> str:
    who_str = ", ".join(who) if isinstance(who, list) else str(who)
    user_content = f'일기="{diary_text}", Who={who_str}, 감정="{emotion}", 장소="{where}", 시간="{when}"'
    return (
        f"A chat between a curious user and an artificial intelligence assistant.\n\n"
        f"{system_prompt}\n\n"
        f"Human: {user_content}\n"
        f"Assistant:\n"
    )


def _parse_output(text: str, fixed_negative: bool = False) -> tuple[dict | None, str]:
    """(파싱 결과, 실패 사유). 성공하면 사유는 빈 문자열."""
    pattern = JSON_PATTERN_POSITIVE_ONLY if fixed_negative else JSON_PATTERN
    # 모델이 JSON 앞뒤로 잡담을 붙이는 경우가 있어서, 정규식으로 JSON 블록만 뽑아냄
    match = pattern.search(text)
    if not match:
        return None, "JSON 블록 없음 (정규식 불일치, 생성이 중간에 잘렸을 수 있음)"
    try:
        result = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        return None, f"JSONDecodeError: {e}"
    if not isinstance(result, dict) or "positive" not in result:
        return None, "positive 키 없음"
    if fixed_negative:
        result["negative"] = FALLBACK_NEGATIVE
    elif "negative" not in result:
        return None, "negative 키 없음"
    return result, ""


def _extract_json(text: str) -> dict | None:
    return _parse_output(text)[0]


def _fallback_prompt(top_emotion: str) -> dict:
    # LLM 변환이 완전히 실패했을 때, 최소한 이미지 생성 자체는 되도록 하는 안전값
    return {
        "positive": f"1girl, solo, {top_emotion}, gamjeong style",
        "negative": FALLBACK_NEGATIVE,
    }


def translate_to_image_prompt(diary_text: str, who, emotion: str, where: str, when: str,
                              gender: str | None = None, config: dict | None = None,
                              report: dict | None = None) -> dict:
    """
    일기 텍스트 -> {"positive": "...", "negative": "..."} 영어 danbooru 태그.
    llm 모드: 기존 일기 생성용 LLaMA를 재사용 (별도 모델 로딩 없음).
    template 모드: LLM 호출 없이 사전 매핑 (image_prompt_template.py 참고). gender는 이 모드에서만 씀.
    config: get_config()에 넘길 덮어쓰기 값 (측정용 디버그 엔드포인트에서 사용)
    report: dict를 넘기면 호출별 측정값을 채워줌 (리턴값은 그대로)
    """
    cfg = get_config(config)
    start = time.time()
    if report is not None:
        report["config"] = cfg
        report["calls"] = []

    if cfg["mode"] == "template":
        from app.services.image_prompt_template import build_template_prompt
        result = build_template_prompt(diary_text=diary_text, who=who, emotion=emotion,
                                       where=where, when=when, gender=gender)
        elapsed = time.time() - start
        print(f"  [이미지 프롬프트 변환] template 모드, LLM 호출 0회, 소요시간: {elapsed * 1000:.1f}ms")
        print(f"  [이미지 프롬프트 변환] positive: {result['positive']}")
        if report is not None:
            report.update(total_sec=round(elapsed, 4), fallback_used=False, **result)
        return result

    from app.services.llama_service import _generate_once, MOCK_MODE

    if MOCK_MODE:
        result = _fallback_prompt(emotion)
        if report is not None:
            report.update(total_sec=0.0, fallback_used=True, **result)
        return result

    system_prompt = build_system_prompt(cfg["num_examples"], cfg["fixed_negative"])
    prompt_str = _build_translation_prompt(diary_text, who, emotion, where, when, system_prompt=system_prompt)
    extra_stops = JSON_CLOSE_STOP_STRINGS if cfg["stop_on_json_close"] else None

    print(f"  [이미지 프롬프트 변환] 설정: {cfg}")

    result = None
    max_attempts = cfg["max_attempts"]
    for attempt in range(1, max_attempts + 1):  # 기본 최대 2번 (JSON 파싱 실패 대비, 너무 오래 끌지 않게)
        stats = {}
        raw = _generate_once(
            prompt_str,
            temperature=cfg["temperature"],
            max_new_tokens=cfg["max_new_tokens"],
            do_sample=cfg["do_sample"],
            extra_stop_strings=extra_stops,
            stats=stats,
        )
        result, fail_reason = _parse_output(raw, cfg["fixed_negative"])

        print(
            f"  [이미지 프롬프트 변환] 호출 {attempt}/{max_attempts} "
            f"({'재시도' if attempt > 1 else '첫 시도'}): "
            f"입력 {stats.get('input_tokens')}토큰, 생성 {stats.get('output_tokens')}토큰"
            f"{' (max_new_tokens 상한 도달)' if stats.get('hit_max_new_tokens') else ''}, "
            f"{stats.get('elapsed_sec')}초, {stats.get('tokens_per_sec')}tok/s, "
            f"파싱 {'성공' if result else '실패 - ' + fail_reason}"
        )
        print("  ----- raw 출력 전문 (Human: 자르기 전) -----")
        print(stats.get("raw_full", raw))
        print("  ----- raw 끝 -----")

        if report is not None:
            report["calls"].append({
                "attempt": attempt,
                "is_retry": attempt > 1,
                "parse_ok": result is not None,
                "fail_reason": fail_reason,
                "raw": raw,
                **stats,
            })

        if result:
            break
        result = None

    elapsed = time.time() - start
    print(f"  [이미지 프롬프트 변환] 소요시간: {elapsed:.1f}초 (LLM 호출 {attempt}회)")

    fallback_used = result is None
    if fallback_used:
        print("  [이미지 프롬프트 변환] 최종 실패, 안전값으로 대체")
        result = _fallback_prompt(emotion)
    else:
        print(f"  [이미지 프롬프트 변환] positive: {result['positive']}")
        print(f"  [이미지 프롬프트 변환] negative: {result['negative']}")

    if report is not None:
        report.update(total_sec=round(elapsed, 2), fallback_used=fallback_used,
                      positive=result["positive"], negative=result["negative"])
    return result
