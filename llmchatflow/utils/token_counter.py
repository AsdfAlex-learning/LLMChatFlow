import logging
from typing import Optional
from transformers import AutoTokenizer
from functools import lru_cache
import re

logger = logging.getLogger(__name__)

@lru_cache(maxsize=128)
def get_tokenizer(model: Optional[str] = None):
    model_name = model or "gpt2"
    try:
        return AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    except Exception as e:
        logger.warning("Failed to load tokenizer: %s (%s)", model_name, str(e))
        return None


def count_tokens(text: str, model: Optional[str] = None) -> int:
    if not text:
        return 0

    tok = get_tokenizer(model)
    if tok is not None:
        try:
            ids = tok.encode(text, add_special_tokens=False)
            return len(ids)
        except Exception as e:
            logger.warning("Failed to encode text for token counting (%s)", str(e))
    return _hybrid_estimate(text)

def _hybrid_estimate(text: str) -> int:
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))
    
    if has_chinese:
        pattern = re.compile(r'([\u4e00-\u9fff])|([a-zA-Z0-9]+)|([^\s])')
        cn_count = 0
        en_count = 0
        sym_count = 0

        for m in pattern.finditer(text):
            cn, en, sym = m.groups()
            if cn:
                cn_count += 1
            elif en:
                en_count += 1
            elif sym:
                sym_count += 1
        return cn_count + en_count + sym_count
        
    else:
        # 纯英文场景不需要正则匹配
        return max(1, int(len(text.split()) * 0.75))