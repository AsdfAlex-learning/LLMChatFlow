# Security Module

该模块负责 LLM 系统中的安全与合规控制，设计目标是 **工程化、低延迟、可配置**。

## 职责
1. **Input Guard**: 在 LLM 推理前检测恶意意图（如 Prompt Injection, Shell 注入）。
2. **Output Guard**: 在响应返回前检测内容合规性（如是否生成了危险命令、是否出现幻觉）。
3. **Decision Making**: 提供结构化的决策结果 (`SafetyDecision`) 供 Router 调度。

## 目录结构
- `decisions.py`: 定义安全决策枚举 (`ALLOW`, `DENY`, `ROUTE_TO_SKILL` 等)。
- `types.py`: 定义通用的检测结果结构 (`SecurityResult`)。
- `policy.py`: 可配置的安全策略 (`SecurityPolicy`)，控制检测的严格程度。
- `input_guard.py`: 输入检测逻辑（正则/关键词）。
- `output_guard.py`: 输出检测逻辑（合规性/幻觉）。

## 使用示例

```python
from src.security import InputGuard, OutputGuard, SecurityPolicy, SafetyDecision

# 初始化
policy = SecurityPolicy(allow_shell_commands=False)
input_guard = InputGuard()
output_guard = OutputGuard()

# 1. 输入检测
result = input_guard.check_input(user_query, policy)
if result.decision == SafetyDecision.DENY:
    return "Refused"

# 2. LLM 推理
response = llm.generate(user_query)

# 3. 输出检测
out_result = output_guard.check_output(response, policy)
if out_result.decision == SafetyDecision.DOWNGRADE:
    return "Filtered response..."
```
