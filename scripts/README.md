# LLM 优化工作流脚本 (Workflow Scripts)

本目录包含了一套完整的 **"数据飞轮" (Data Flywheel)** 脚本，用于自动化地生成数据、评测模型、筛选样本并进行微调。

通过这套流程，你可以利用更强的模型（如 DeepSeek/GPT-4）来蒸馏和优化你的本地小模型（如 Qwen2.5-3B）。

## 🚀 工作流概览

1.  **启动 (Bootstrap)**: 跑通本地推理服务。
2.  **模拟 (Simulate)**: 让大模型扮演用户，与本地模型聊天，生成原始对话数据。
3.  **评测 (Evaluate)**: 让大模型扮演裁判，给本地模型的回答打分。
4.  **准备 (Prepare)**: 筛选高分数据，转换为训练格式。
5.  **训练 (Train)**: 使用 LoRA 微调本地模型。
6.  **重测 (Rerun)**: 验证微调后的效果提升。

---

## 📜 脚本详解

### 1. `01_bootstrap_model.py`
**启动本地推理服务并记录初始状态。**
*   **功能**: 启动 `src.llm_system.server.app`，并在 MLflow 中记录初始实验参数。
*   **用途**: 跑通最基础的推理流程，确认环境就绪。
*   **用法**:
    ```bash
    python scripts/01_bootstrap_model.py --model_path "Qwen/Qwen2.5-3B-Instruct"
    ```

### 2. `02_simulate_dialogue.py`
**模拟多轮对话。**
*   **功能**: 调用 DeepSeek API 扮演用户，向本地模型提问并追问，生成 `simulation_data.json`。
*   **目的**: 生成用于后续分析的“代理用户偏好指标”数据源。
*   **配置**: 自动读取 `config/system.yaml` 中的 API Key，无需手动输入。
*   **用法**:
    ```bash
    python scripts/02_simulate_dialogue.py
    ```

### 3. `03_evaluate_responses.py`
**质量评测 (LLM-as-a-Judge)。**
*   **功能**: 让 DeepSeek 对生成的对话进行多维度打分（准确性、有用性、连贯性），生成 `evaluation_results.json`。
*   **注意**: 
    *   这里关注的是聊天体验，而非 OpenCompass 侧重的通用能力评测。
    *   LLM 裁判的打分仅供参考，**不是真值**。
*   **用法**:
    ```bash
    python scripts/03_evaluate_responses.py
    ```

### 4. `04_prepare_sft_data.py`
**数据筛选与格式转换。**
*   **功能**: 根据评分筛选高质量对话（默认 > 4.0 分），转换为 SFT 训练所需的 JSONL 格式 (`sft_train.jsonl`)。
*   **风险提示**: 这种基于高分筛选的方法**可能引入分布偏差**，需留意模型是否过度拟合裁判的喜好。
*   **用法**:
    ```bash
    python scripts/04_prepare_sft_data.py --min_score 4.0
    ```

### 5. `05_train_lora.py`
**LoRA 微调训练。**
*   **功能**: 使用筛选出的数据对模型进行 4-bit QLoRA 微调，保存 Checkpoint。
*   **用法**:
    ```bash
    python scripts/05_train_lora.py --model_path "Qwen/Qwen2.5-3B-Instruct"
    ```

### 6. `06_rerun_evaluation.py`
**回归测试与对比。**
*   **功能**: 在微调后的模型上重新运行模拟和评测流程，用于在 MLflow 中观察**在代理指标下的相对变化**。
*   **用法**:
    ```bash
    python scripts/06_rerun_evaluation.py --model_path "checkpoints/lora_v1"
    ```

---

## ⚙️ 自动化配置

脚本 `02`, `03`, `06` 依赖外部 LLM API（如 DeepSeek）。
为了方便使用，它们会自动读取项目根目录下 `config/system.yaml` 中的配置：

```yaml
llm:
  api_key: "sk-..."        # 自动用于模拟器和裁判
  api_url: "..."           # 自动处理 /chat/completions 后缀
  model: "deepseek-chat"   # 默认使用的模拟/裁判模型
```

这意味着你通常**不需要**在命令行中传递 `--api_key` 参数，除非你想覆盖默认配置。

---

## 📊 MLflow 集成

所有脚本都会自动将运行参数、生成的 Artifact（JSON/JSONL 文件）和指标（分数、Loss）记录到 MLflow。

查看实验结果：
```bash
mlflow ui
```
然后访问 http://localhost:5000 查看 `LLM_Bootstrap` 实验。
