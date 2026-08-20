from pathlib import Path

# kobert_model/emotion24-bert 폴더는 종현이가 준 model/emotion24-bert 그대로 복사한 것
MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "kobert_model" / "emotion24-bert"
MAX_LEN = 64

_tokenizer = None
_model = None
_device = None


def get_model_and_tokenizer():
    # torch/transformers는 여기 안에서만 import함 (llama_loader랑 같은 이유 - Mock 모드/테스트에서 안 불려도 됨)
    global _tokenizer, _model, _device
    if _model is None:
        import torch
        from transformers import AutoTokenizer, BertForSequenceClassification

        # LLaMA가 cuda:0 쓰고 있으니까 KoBERT는 다른 GPU로 분리
        # (KoBERT는 용량 작아서 사실 같은 GPU에 껴도 되지만, 명확하게 분리해두는 게 안전함)
        _device = torch.device("cuda:1" if torch.cuda.is_available() else "cpu")

        print("KoBERT(24개 감정분류) 모델 로딩 중... (최초 1회만)")
        _tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))
        _model = BertForSequenceClassification.from_pretrained(str(MODEL_DIR))
        _model.to(_device)
        _model.eval()
        print("KoBERT 모델 로딩 완료")

    return _model, _tokenizer, _device