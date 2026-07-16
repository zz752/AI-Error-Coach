# AI错题教练 Skill

> 基于大语言模型的智能错题分析工具 —— 帮助学生从"做错一道题"到"彻底掌握一个知识点"。

---

## 项目简介

AI错题教练是一个可复用的 LLM Skill，专为 K12 学生和教师设计。只需输入一道错题的题干、学生答案、正确答案和学科，系统自动完成四件事：

1. **错题原因分析** — 定位错误类型、分析原因、标定知识漏洞
2. **生成类似题** — 针对薄弱知识点，生成同难度练习题
3. **制定复习计划** — 根据错误情况生成 7 天分阶段复习方案
4. **导出上传飞书** — 生成 Markdown 学习报告并上传至飞书云文档

---

## 项目结构

```
AI-Error-Coach/
├── skill/                           # Skill 核心包
│   ├── SKILL.md                     # Skill 定义（触发器、流程、约定）
│   ├── scripts/
│   │   ├── analyze_error.py         # 功能1：错题原因分析
│   │   ├── generate_question.py     # 功能2：生成类似练习题
│   │   ├── review_plan.py           # 功能3：生成 7 天复习计划
│   │   └── upload_feishu.py         # 功能4：导出报告并上传飞书
│   └── references/
│       ├── error_types.md           # 错误类型分类体系（6大类+学科细分）
│       └── prompt_templates.md      # 三组 LLM Prompt 模板
│
├── data/
│   └── wrong_questions.json         # 测试数据集（9条，7学科，6种错误类型）
│
├── output/                          # 生成的学习报告（.md 文件）
│
├── tests/
│   └── test_record.md               # 测试记录（环境、步骤、用例、结论）
│
├── iteration/
│   └── iteration_log.md             # 迭代日志与扩展方案
│
└── README.md                        # 本文档
```

---

## 快速开始

### 环境要求

- Python ≥ 3.9
- OpenAI API 账号及 API Key

### 安装

```bash
# 1. 安装依赖
pip install openai requests

# 2. 设置环境变量（LLM 相关）
export OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxx"     # 必填
export OPENAI_MODEL="gpt-4o"                       # 可选，默认 gpt-4o
export OPENAI_BASE_URL="https://api.openai.com/v1" # 可选，默认官方地址
export OPENAI_TEMPERATURE="0.3"                    # 可选，默认 0.3

# 3. 设置环境变量（飞书上传相关，仅功能4需要）
export FEISHU_APP_ID="cli_xxxxxxxxxxxx"            # 飞书应用 App ID
export FEISHU_APP_SECRET="xxxxxxxxxxxxxxxxxxxxx"   # 飞书应用 App Secret
export FEISHU_FOLDER_TOKEN="xxxxx"                 # 可选，上传目标文件夹
```

### 使用

#### 功能1：错题原因分析

```bash
python skill/scripts/analyze_error.py \
  --question "已知函数 f(x)=x²-4x+3，求 f(x) 的最小值。" \
  --student_answer "3" \
  --correct_answer "-1，在 x=2 处取得。" \
  --subject "数学"
```

**输出示例**：

```
==================================================
📊 分析结果
==================================================
学科：数学
错误类型：概念混淆
错误原因：学生混淆了二次函数一般式常数项与最小值...
涉及知识点：二次函数、顶点坐标公式、函数最值、配方法
==================================================
```

#### 功能2：生成类似题

```bash
# 方式A：直接传参
python skill/scripts/generate_question.py \
  --knowledge_points "二次函数,顶点坐标,配方法" \
  --subject "数学" \
  --error_type "概念混淆"

# 方式B：从分析结果文件读取
python skill/scripts/generate_question.py --from-file analysis.json
```

#### 功能3：生成复习计划

```bash
# 方式A：直接传参
python skill/scripts/review_plan.py \
  --error_type "概念混淆" \
  --knowledge_points "二次函数,顶点坐标,配方法" \
  --subject "数学"

# 方式B：从分析结果文件读取
python skill/scripts/review_plan.py --from-file analysis.json
```

#### 功能4：导出报告 & 上传飞书

```bash
# 方式A：指定三个 JSON 文件
python skill/scripts/upload_feishu.py \
  --analysis output/analysis.json \
  --similar output/similar_question.json \
  --review output/review_plan.json

# 方式B：指定 output 目录（自动匹配文件名）
python skill/scripts/upload_feishu.py --output-dir output/

# 方式C：仅生成本地报告，不上传飞书
python skill/scripts/upload_feishu.py \
  --analysis output/analysis.json \
  --review output/review_plan.json \
  --no-upload
```

**输出示例**：

```
☁️  正在上传至飞书云文档...
   1/3 获取飞书访问令牌...
   ✅ 令牌获取成功
   2/3 上传文件...
   ✅ 文件上传成功
   3/3 完成

======================================================
✅ 报告生成 & 飞书上传完成！
======================================================
   📁 本地文件：output/learning_report_20260716_143000.md
   🔑 file_token：BxTnfGxxxxxx
   🔗 飞书链接：https://xxxxx.feishu.cn/drive/xxxxx
======================================================
```

**上传后效果**：
- 学习报告自动上传至飞书云文档（Drive）
- 支持在飞书客户端内直接预览 Markdown 格式报告
- 可在飞书群聊中分享文档链接，方便教师/家长查看

---

## 测试

```bash
# 查看测试数据集
cat data/wrong_questions.json

# 运行单题分析测试
python skill/scripts/analyze_error.py \
  --question "If I ___ you, I would accept the offer." \
  --student_answer "was" \
  --correct_answer "were" \
  --subject "英语"

# 完整测试记录见
cat tests/test_record.md
```

测试数据集覆盖 7 个学科、6 种错误类型的 9 道真实错题。

---

## 设计亮点

| 特性 | 说明 |
|------|------|
| **零硬编码密钥** | 全部从环境变量读取 `OPENAI_API_KEY` |
| **Prompt 与代码解耦** | 模板集中在 `references/prompt_templates.md`，改 Prompt 不需改代码 |
| **错误分类可扩展** | 在 `references/error_types.md` 新增分类，脚本自动加载 |
| **健壮容错** | JSON 解析异常、API 调用失败、references 缺失均有回退策略 |
| **可串联调用** | `generate_question.py` 和 `review_plan.py` 支持 `--from-file` 读取上一环节输出 |
| **双格式输出** | 同时输出人类可读格式和标准 JSON（供程序对接） |
| **飞书集成** | 自动导出 Markdown 学习报告并上传飞书云文档 |

---

## 错误类型体系

| 类型 | 典型表现 |
|------|----------|
| 概念混淆 | 公式混淆、定理用错、词义误读 |
| 计算失误 | 符号错误、进位错误、遗漏换算 |
| 审题偏差 | 漏看条件、答非所问、忽略限定 |
| 知识盲区 | 完全不了解该知识点 |
| 逻辑推理错误 | 因果关系倒置、分类讨论不全 |
| 解题策略不当 | 用复杂方法解简单题、选错公式 |

---

## 未来扩展

| 方向 | 说明 | 详细方案 |
|------|------|----------|
| 图片题 OCR 支持 | 拍照 → OCR 识别 → 自动提取题干 | 见 `iteration/iteration_log.md` § 3.1 |
| 知识图谱扩展 | 构建学科知识图谱，精准定位漏洞 | 见 `iteration/iteration_log.md` § 3.2 |
| 飞书报告上传 | 自动导出并上传学习报告至飞书云文档 | ✅ 已实现（v1.1.0） |
| 多用户学习记录 | 数据库存储历史，追踪进步曲线 | 见 `iteration/iteration_log.md` § 3.4 |

---

## 技术栈

- **语言**：Python 3.9+
- **LLM**：OpenAI GPT-4o（可替换为兼容 API）
- **SDK**：openai ≥ 1.0.0, requests ≥ 2.28.0
- **输出格式**：JSON（结构化） + Markdown（学习报告） + 控制台（人类可读）
- **云存储**：飞书开放平台 Drive API

---

## 作者

课程项目 — AI Agent 工程实践

---

## 许可

MIT License
