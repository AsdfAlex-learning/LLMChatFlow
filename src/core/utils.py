
def get_clean_api_base(url: str) -> str:
    """
    清理 API URL，移除 /chat/completions 后缀，确保符合 OpenAI SDK 要求
    """
    if not url:
        return ""
    
    url = url.strip()
    if url.endswith("/chat/completions"):
        url = url[:-17]
    
    # 去除末尾的斜杠
    if url.endswith("/"):
        url = url[:-1]
        
    return url
