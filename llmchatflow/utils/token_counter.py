from typing import Optional
from transformers import AutoTokenizer

_TOKENIZER_CACHE = {}


def _get_tokenizer(model: Optional[str] = None):
    key = model or "gpt2"
    if key in _TOKENIZER_CACHE:
        return _TOKENIZER_CACHE[key]
    candidates = [c for c in [model, "gpt2"] if c]
    for name in candidates:
        try:
            tok = AutoTokenizer.from_pretrained(name, trust_remote_code=True)
            _TOKENIZER_CACHE[key] = tok
            return tok
        except Exception:
            continue
    _TOKENIZER_CACHE[key] = None
    return None


def count_tokens(text: str, model: Optional[str] = None) -> int:
    tok = _get_tokenizer(model)
    if tok is None:
        return len(text.split())
    try:
        ids = tok.encode(text, add_special_tokens=False)
        return len(ids)
    except Exception:
        return len(text.split())
