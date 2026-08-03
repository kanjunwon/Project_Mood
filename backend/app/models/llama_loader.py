MODEL_ID = "yanolja/EEVE-Korean-Instruct-10.8B-v1.0"

_tokenizer = None
_model = None


def get_model_and_tokenizer():
    global _tokenizer, _model
    if _model is None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from app.config import HF_TOKEN

        print("LLaMA(EEVE) 모델 로딩 중... (최초 1회만)")
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, token=HF_TOKEN)
        if _tokenizer.pad_token is None:
            _tokenizer.pad_token = _tokenizer.eos_token
        _tokenizer.padding_side = "left"
        _model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            token=HF_TOKEN,
        )
        print("모델 로딩 완료")
    return _model, _tokenizer
