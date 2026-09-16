from pathlib import Path

# kobert_model/emotion24-bert 폴더는 종현이가 준 model/emotion24-bert 그대로 복사한 것
MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "kobert_model" / "emotion24-bert"
MAX_LEN = 128  # 64였을 때 실제 일기(3~5문장)가 잘려서 뒷부분(긍정적 마무리 등)이 모델에 안 보이는 문제 발견, 늘림

_tokenizer = None
_model = None
_device = None


def get_model_and_tokenizer():
    # torch/transformers는 여기 안에서만 import함 (llama_loader랑 같은 이유 - Mock 모드/테스트에서 안 불려도 됨)
    global _tokenizer, _model, _device
    if _model is None:
        import torch
        from transformers import AutoTokenizer, BertForSequenceClassification

        # LLaMA가 cuda:0 쓰니까 GPU 2개 이상인 환경(학교 서버)에선 KoBERT를 cuda:1로 분리.
        # GPU 1개짜리 환경(RunPod 등)에서는 cuda:1이 존재하지 않아 "invalid device ordinal" 에러가
        # 나는 걸 2026-09-14 RunPod 테스트에서 확인 -> GPU 개수를 실제로 확인해서 자동으로 맞추도록 수정.
        if torch.cuda.is_available():
            _device = torch.device("cuda:1" if torch.cuda.device_count() > 1 else "cuda:0")
        else:
            _device = torch.device("cpu")

        print(f"KoBERT(24개 감정분류) 모델 로딩 중... (최초 1회만, device={_device})")
        _tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))
        _model = BertForSequenceClassification.from_pretrained(str(MODEL_DIR))
        _model.to(_device)
        _model.eval()
        print("KoBERT 모델 로딩 완료")

    return _model, _tokenizer, _device