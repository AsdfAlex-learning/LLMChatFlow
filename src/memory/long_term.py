class LongTermMemory:
    """
    长期记忆 (Episodic / Semantic Memory)
    负责存储重要的对话摘要、事实性信息
    通常需要向量数据库支持，这里先做简单的接口抽象
    """
    
    def __init__(self):
        # 简单示例：用列表模拟
        self.memories = []

    def remember(self, content: str, tags: list = None):
        """存储一条长期记忆"""
        self.memories.append({
            "content": content,
            "tags": tags or [],
            "timestamp": "..."
        })
        
    def recall(self, query: str) -> list:
        """检索相关记忆"""
        # TODO: 实现语义搜索
        return [m for m in self.memories if query in m["content"]]
