from typing import Optional
from transformers import AutoTokenizer
import re

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
    if tok is not None:
        try:
            ids = tok.encode(text, add_special_tokens=False)
            return len(ids)
        except Exception:
            return _hybrid_estimate(text)
    return _hybrid_estimate(text)

def _hybrid_estimate(text: str) -> int:
    if not text:
        return 0
    
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))

    if has_chinese: # 混合/中文场景
        cn = re.findall(r'[\u4e00-\u9fff]', text)
        en = re.findall(r'[a-zA-Z0-9]+', text)    # 匹配所有英文、数字,连续的算一个
        sym = re.findall(r'[^\u4e00-\u9fffa-zA-Z0-9\s]', text)    # 匹配所有标点、符号（不含空格）
        return len(cn) + len(en) + len(sym)
    else:
        return len(text.split())  # 纯英文场景 则按空格分割 估算token