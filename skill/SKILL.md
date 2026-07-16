---
name: AI错题教练
version: 1.1.0
author: course-project
description: >
  智能错题分析 Skill。接收学生的错题信息（题目、学生答案、正确答案、学科），
  自动执行错误原因分析、生成同类练习题、制定个性化 7 天复习计划，
  并将学习报告导出上传至飞书云文档。
triggers:
  - 错题分析
  - 分析错题
  - 错题教练
  - 生成类似题
  - 复习计划
  - AI错题
  - error coach
  - 飞书上传
  - 导出报告
  - 上传飞书
input_schema:
  question_content:
    type: string
    required: true
    description: 错题的完整题干内容
  student_answer:
    type: string
    required: true
    description: 学生给出的错误答案
  correct_answer:
    type: string
    required: true
    description: 题目的正确答案
  subject:
    type: string
    required: true
    enum:
      - 数学
      - 语文
      - 英语
      - 物理
      - 化学
      - 生物
      - 历史
      - 地理
      - 政治
      - 其他
    description: 所属学科
output_schema:
  error_analysis:
    type: object
    fields:
      error_type: string        # 错误类型分类
      error_reason: string      # 具体错误原因分析
      knowledge_points: list    # 涉及的知识点
  similar_question:
    type: object
    fields:
      question: string          # 生成的类似题题干
      answer: string            # 类似题答案
      explanation: string       # 解题思路
  review_plan:
    type: object
    fields:
      day_1~7: object           # 每天的学习任务
      total_review_items: int   # 复习知识点总数
      estimated_hours: float    # 预估总时长
  feishu_upload:
    type: object
    fields:
      file_token: string        # 飞书文件 token
      document_url: string      # 飞书文档链接
      local_path: string        # 本地报告路径
scripts:
  - path: skill/scripts/analyze_error.py
    purpose: 错题原因分析
    inputs: [question_content, student_answer, correct_answer, subject]
  - path: skill/scripts/generate_question.py
    purpose: 生成类似练习题
    inputs: [knowledge_points, subject, error_type]
  - path: skill/scripts/review_plan.py
    purpose: 生成 7 天复习计划
    inputs: [error_type, knowledge_points, subject]
  - path: skill/scripts/upload_feishu.py
    purpose: 生成学习报告并上传飞书云文档
    inputs: [analysis_json, similar_json, review_json]
references:
  - skill/references/error_types.md
  - skill/references/prompt_templates.md
---

# AI错题教练

## 概述

AI错题教练是一个面向学生和教师的智能错题分析 Skill。输入一道错题的相关信息，Skill 会依次执行四个核心功能：**错题原因分析** → **生成类似练习题** → **制定 7 天复习计划** → **导出报告并上传飞书**，帮助学生从"做错一道题"到"彻底掌握一个知识点"。

## 适用场景

- 学生日常整理错题本，需要快速定位知识漏洞
- 教师批改作业后，需要批量生成针对性练习
- 考前复习阶段，需要根据历史错题制定复习方案
- 自适应学习系统中作为错题分析引擎

## 执行流程

```
用户输入（错题信息）
       │
       ▼
┌──────────────────────┐
│  Step 1: 错题原因分析  │  ← scripts/analyze_error.py
│  输出: 错误类型 +      │
│        错误原因 +      │
│        涉及知识点      │
└──────────┬───────────┘
           │ 知识点列表
           ▼
┌──────────────────────┐
│  Step 2: 生成类似题   │  ← scripts/generate_question.py
│  输出: 同知识点、      │
│        同难度练习题 +  │
│        答案 + 解题思路  │
└──────────┬───────────┘
           │ 错误类型 + 知识点
           ▼
┌──────────────────────┐
│  Step 3: 生成复习计划  │  ← scripts/review_plan.py
│  输出: 7天分阶段方案   │
└──────────┬───────────┘
           │ 全部分析结果
           ▼
┌──────────────────────┐
│  Step 4: 导出 & 上传  │  ← scripts/upload_feishu.py
│  输出: Markdown报告 +  │
│        飞书文档链接    │
└──────────┬───────────┘
           │
           ▼
     完整分析报告 & 飞书链接
```

## 输入说明

调用此 Skill 时，需提供以下信息：

| 字段 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `question_content` | string | ✅ | 错题完整题干 | "已知函数 f(x)=x²-4x+3，求 f(x) 的最小值" |
| `student_answer` | string | ✅ | 学生的错误答案 | "-1" |
| `correct_answer` | string | ✅ | 正确答案 | "-1（在 x=2 处取得）" ← *注：此处示例演示关键信息包含* |
| `subject` | string | ✅ | 学科（枚举值） | "数学" |

**学科枚举值**：`数学` `语文` `英语` `物理` `化学` `生物` `历史` `地理` `政治` `其他`

## 输出说明

### 功能1 — 错题原因分析

```json
{
  "error_type": "概念混淆",
  "error_reason": "学生混淆了一次函数与二次函数的顶点公式，误将对称轴公式 x=-b/2a 记为 x=-b/a",
  "knowledge_points": ["二次函数", "顶点坐标", "配方法"]
}
```

### 功能2 — 生成类似题

```json
{
  "question": "已知函数 g(x)=2x²-8x+7，求 g(x) 的最小值及对应的 x 值。",
  "answer": "最小值为 -1，在 x=2 处取得",
  "explanation": "利用二次函数顶点公式 x=-b/(2a)，代入得 x=8/(4)=2，g(2)=2×4-16+7=-1"
}
```

### 功能3 — 复习计划

```json
{
  "plan": {
    "day_1": "回顾二次函数顶点公式 x=-b/(2a)，做 5 道基础题",
    "day_2": "练习配方法求顶点，对比公式法",
    "day_3": "二次函数图像性质：开口方向、对称轴、顶点",
    "day_4": "二次函数最值应用题 3 道",
    "day_5": "综合练习：二次函数与一元二次方程关系",
    "day_6": "错题重做 + 变式训练",
    "day_7": "限时自测 + 总结归纳"
  },
  "total_review_items": 5,
  "estimated_hours": 3.5
}
```

### 功能4 — 导出并上传飞书

```json
{
  "status": "success",
  "local_path": "/path/to/output/learning_report_20260716_143000.md",
  "file_token": "BxTnfGxxxxxx",
  "document_url": "https://xxxxx.feishu.cn/drive/xxxxx",
  "folder_token": "root",
  "timestamp": "2026-07-16T14:30:00"
}
```

## 调用脚本说明

### analyze_error.py

```bash
python skill/scripts/analyze_error.py \
  --question "题目内容" \
  --student_answer "学生答案" \
  --correct_answer "正确答案" \
  --subject "数学"
```

调用 OpenAI API，参考 `skill/references/error_types.md` 中的错误分类体系和 `skill/references/prompt_templates.md` 中的 Prompt 模板进行分析。返回结构化 JSON。

### generate_question.py

```bash
python skill/scripts/generate_question.py \
  --knowledge_points "二次函数,顶点坐标" \
  --subject "数学" \
  --error_type "概念混淆"
```

根据知识点和错误类型，生成 1 道难度相近的类似题，附带答案和解题思路。

### review_plan.py

```bash
python skill/scripts/review_plan.py \
  --error_type "概念混淆" \
  --knowledge_points "二次函数,顶点坐标,配方法" \
  --subject "数学"
```

根据错误类型和知识点，制定 7 天分阶段复习计划，包含每天具体任务。

### upload_feishu.py

```bash
python skill/scripts/upload_feishu.py \
  --analysis output/analysis.json \
  --similar output/similar_question.json \
  --review output/review_plan.json

# 也可以通过 --output-dir 自动加载
python skill/scripts/upload_feishu.py --output-dir output/

# 仅生成立报告，不上传飞书
python skill/scripts/upload_feishu.py --analysis output/analysis.json --review output/review_plan.json --no-upload
```

合并前三步结果生成 Markdown 学习报告，保存到 `output/` 目录，调用飞书开放平台 API 上传至云文档 Drive，返回 `file_token` 和 `document_url`。

## 依赖

- Python 3.9+
- `openai` Python SDK（`pip install openai`）
- `requests` Python 库（`pip install requests`，用于飞书 API 调用）
- 有效的 OpenAI API Key（设置环境变量 `OPENAI_API_KEY`）
- 飞书开放平台应用凭证（设置环境变量 `FEISHU_APP_ID` / `FEISHU_APP_SECRET`）—— 仅功能4需要

## 配置

```bash
# LLM 相关（功能1-3 必需）
export OPENAI_API_KEY="sk-xxx"
export OPENAI_MODEL="gpt-4o"          # 可选，默认 gpt-4o
export OPENAI_TEMPERATURE="0.3"       # 可选，默认 0.3

# 飞书上传（功能4 必需）
export FEISHU_APP_ID="cli_xxxxxxxxxxxx"
export FEISHU_APP_SECRET="xxxxxxxxxxxxxxxxxxxxxxxxxx"
export FEISHU_FOLDER_TOKEN="xxxxx"    # 可选，上传目标文件夹
```

## 注意事项

1. **API 调用成本**：每次完整分析会调用 3 次 OpenAI API（分析 + 出题 + 复习计划）+ 1 次飞书 API（上传），请注意 token 消耗。
2. **Prompt 可定制**：如需调整分析风格、出题难度等，修改 `skill/references/prompt_templates.md` 即可，无需改代码。
3. **错误类型扩展**：如需新增错误分类，在 `skill/references/error_types.md` 中添加即可，脚本会自动加载。
4. **独立运行**：四个脚本可独立使用，也可串联使用。若已有分析结果，可直接调用 `generate_question.py`、`review_plan.py` 或 `upload_feishu.py`。
5. **飞书上传**：功能4 需要先在飞书开放平台创建应用并获取 App ID 和 App Secret，详见飞书开放平台文档。
