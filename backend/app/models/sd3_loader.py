"""
app/models/sd3_loader.py
재유 담당 - 그림일기 이미지 생성 (파일명은 sd3지만 실제로는 SDXL/Illustrious 사용 중)

⚠️ 히스토리: 처음엔 SD3+LoRA로 시작했으나, 손/인체 왜곡과 다인원 붕괴 문제가
디테일러 파이프라인으로도 해결이 안 돼서 베이스 모델을 SDXL 계열로 교체함.
여러 후보(Illustrious XL, Animagine XL, FLUX.1, DreamShaper XL) 검토 후
Illustrious XL v1.0(raw checkpoint)을 최종 베이스로 확정.
파일명(sd3_loader.py/sd3_service.py)은 팀 README 담당 배정 그대로 유지하기 위해
안 바꿨고, 내부 로직만 SDXL/Illustrious 기준으로 맞춤.

이미지 생성 자체는 diffusers 직접 로딩 대신 ComfyUI API를 통해 처리.
검증 끝난 ComfyUI 워크플로우(체크포인트 로드+LoRA 로드+CLIP 인코딩 x2+KSampler+VAE 디코드)를
API 형식으로 export해서 그대로 재사용한다.

사용 LoRA: gamjeong_illustrious_v1.safetensors

사전 준비:
1. 학교 서버에서 ComfyUI를 API 모드로 실행: python main.py --listen 0.0.0.0 --port 8188
2. ComfyUI 설정에서 "Enable Dev mode Options" 체크 (Save API Format 버튼이 기본 숨김이라 필요)
3. 워크플로우를 "Save (API Format)"으로 export ("Save"랑 다른 버튼이니 주의)
4. export한 JSON을 app/comfyui_workflow.json으로 저장
"""
import json
import os
from pathlib import Path

# FastAPI 서버와 ComfyUI가 같은 머신이면 localhost, 다른 서버면 실제 주소를 .env에 설정
# (다른 네트워크에서 접근해야 하면 ngrok 등으로 터널링한 주소를 넣으면 됨)
COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")

EXPECTED_LORA_FILENAME = "gamjeong_illustrious_v1.safetensors"

_WORKFLOW_PATH = Path(__file__).resolve().parent.parent / "comfyui_workflow.json"
_workflow_template_cache: dict | None = None


def load_workflow_template() -> dict:
    """ComfyUI API 형식 워크플로우 JSON을 로드 (최초 1회만 읽고 캐싱, 매번 깊은 복사해서 반환)"""
    global _workflow_template_cache
    if _workflow_template_cache is None:
        if not _WORKFLOW_PATH.exists():
            raise FileNotFoundError(
                f"{_WORKFLOW_PATH} 없음 - ComfyUI에서 'Save (API Format)'으로 export한 "
                "워크플로우 JSON을 이 경로에 저장해야 함"
            )
        with open(_WORKFLOW_PATH, "r", encoding="utf-8") as f:
            template = json.load(f)

        # sanity check: 워크플로우 안에 우리가 학습한 LoRA 파일명이 실제로 들어있는지 확인
        # (다른 LoRA나 옛날 SD3용 워크플로우를 잘못 export해서 넣는 실수 방지)
        lora_found = any(
            node.get("inputs", {}).get("lora_name") == EXPECTED_LORA_FILENAME
            for node in template.values()
            if isinstance(node, dict)
        )
        if not lora_found:
            raise ValueError(
                f"comfyui_workflow.json 안에 LoRA '{EXPECTED_LORA_FILENAME}'가 안 보임 - "
                "다른 워크플로우를 export한 게 아닌지 확인 필요"
            )

        _workflow_template_cache = template
    return json.loads(json.dumps(_workflow_template_cache))  # 매 요청마다 독립된 복사본
