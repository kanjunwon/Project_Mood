import importlib.util
import os
from pathlib import Path

os.environ["MOCK_MODE"] = "true"

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "measure_image_prompt.py"
_spec = importlib.util.spec_from_file_location("measure_image_prompt", _SCRIPT)
measure = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(measure)


def _call(attempt, inp, out, sec, ok=True, hit=False):
    return {"attempt": attempt, "input_tokens": inp, "output_tokens": out, "elapsed_sec": sec,
            "tokens_per_sec": round(out / sec, 2), "parse_ok": ok, "hit_max_new_tokens": hit,
            "fail_reason": "" if ok else "JSON 블록 없음"}


def _run(phase, label, case, sec, positive, calls=None, fallback=False):
    return {"phase": phase, "label": label, "case": case, "total_sec": sec, "positive": positive,
            "calls": calls or [], "fallback_used": fallback}


BASE_POS = "1girl, solo, young adult woman, cafe, laptop, smiling, gamjeong style"


def _fake_data():
    runs = [
        _run("baseline", "현재 설정", "A", 93.5, BASE_POS,
             [_call(1, 2900, 200, 46.0, ok=False, hit=True), _call(2, 2900, 180, 47.0)]),
        _run("baseline", "현재 설정", "B", 50.0, "1girl, 2boys, mature female, mother, gamjeong style",
             [_call(1, 2850, 170, 50.0)]),
        _run("template", "template", "A", 0.001, "1girl, solo, young adult woman, cafe, gamjeong style"),
        _run("template", "template", "B", 0.001, "1girl, 2boys, mature female, mother, gamjeong style"),
        # 빠르고 비슷함
        _run("combined", "모두적용", "A", 20.0, "1girl, solo, young adult woman, cafe, smiling, gamjeong style",
             [_call(1, 1300, 60, 20.0)]),
        _run("combined", "모두적용", "B", 25.0, "1girl, 2boys, mature female, mother, gamjeong style",
             [_call(1, 1300, 70, 25.0)]),
        # 제일 빠르지만 인원수가 바뀜
        _run("single", "greedy", "A", 15.0, "2girls, cafe, gamjeong style", [_call(1, 2900, 50, 15.0)]),
        # 느림
        _run("single", "stop", "A", 60.0, BASE_POS, [_call(1, 2900, 150, 60.0)]),
    ]
    return {"started_at": "test", "env": {}, "runs": runs, "pipeline": [], "skipped": [], "model_info": None}


def test_summary_baseline_row_shows_retry_and_tokens():
    s = measure.render_summary(_fake_data())
    assert "| A | 93.5 | 2 | O | 2900 / 2900 | 200* / 180 | " in s
    assert "| B | 50.0 | 1 | X | 2850 | 170 | " in s


def test_summary_target_ox_per_combo():
    s = measure.render_summary(_fake_data())
    assert "| baseline | 현재 설정 | 2 | 71.75 | 93.5 | 0/2 | X |" in s
    assert "| combined | 모두적용 | 2 | 22.5 | 25.0 | 0/2 | O |" in s
    assert "| single | stop | 1 | 60.0 | 60.0 | 0/1 | X |" in s


def test_summary_template_missing_tags():
    s = measure.render_summary(_fake_data())
    assert "| A | 0.001 | laptop, smiling |" in s
    assert "| B | 0.001 | (없음) |" in s


def test_summary_fastest_three_and_similar_pick():
    s = measure.render_summary(_fake_data())
    section = s.split("### 4.")[1]
    rows = [l for l in section.splitlines() if l.startswith("| 1 ") or l.startswith("| 2 ") or l.startswith("| 3 ")]
    assert [r.split(" | ")[2] for r in rows] == ["greedy", "모두적용", "stop"]
    assert rows[0].endswith("| X |")  # 인원 태그가 바뀌어서 비슷하지 않음
    assert rows[1].endswith("| O |")
    assert "품질이 현재와 비슷한 조합: **모두적용**" in s


def test_summary_and_markdown_with_no_results():
    empty = {"started_at": "t", "env": {}, "runs": [], "pipeline": [], "skipped": ["x"], "model_info": None}
    assert "기준을 만족하는 조합 없음" in measure.render_summary(empty)
    md = measure.render_markdown(empty)
    assert md.startswith("# 이미지 프롬프트 변환 측정") and "## 해석용 요약" in md
