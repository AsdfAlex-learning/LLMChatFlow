"""
文件职责：上下文数据结构
管理单次对话的短期记忆（Context），包括：
- 摘要 (Summary)：上一段对话的精简摘要。
- 近期消息 (Recent Messages)：最近 N 条对话的逐字记录。
负责格式化这些数据以供 Prompt 使用。
"""

from typing import List, Dict, Optional

class ConversationContext:
    """
    管理短期记忆（对话历史），结构如下：
    - 摘要 (Summary)
    - 近期消息 (Recent Messages)
    """
    def __init__(self, max_history: int = 20):
        self.history: List[Dict[str, str]] = []
        self.summary: str = "暂无前情提要"
        self.max_history = max_history

    def add_message(self, role: str, content: str):
        """添加一条消息到历史记录。"""
        self.history.append({"role": role, "content": content})
        # 维持固定窗口大小
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    def update_summary(self, new_summary: str):
        """更新对话摘要。"""
        if new_summary:
            self.summary = new_summary

    def format(self, exclude_last_n: int = 0) -> str:
        """将上下文格式化为 Prompt 字符串。"""
        lines = []
        
        # 1. 摘要部分
        lines.append("【前情提要】")
        lines.append(self.summary)
        lines.append("") # 空行
        
        # 2. 近期对话部分
        lines.append("【近期对话】")
        
        msgs_to_show = self.history[:-exclude_last_n] if exclude_last_n > 0 else self.history
        
        if not msgs_to_show:
            lines.append("（暂无近期对话）")
        else:
            for msg in msgs_to_show:
                role_name = "User" if msg["role"] == "user" else "AI"
                lines.append(f"{role_name}: {msg['content']}")
        
        return "\n".join(lines)

    def get_raw_history(self) -> List[Dict[str, str]]:
        return self.history
