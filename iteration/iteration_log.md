# AI错题教练 — 迭代日志

> 记录每次版本更新的内容、决策依据和未来规划。

---

## 1. 版本历史

### v1.1.0 — 飞书上传模块（2026-07-16）

**发布内容**：

| 模块 | 文件 | 说明 |
|------|------|------|
| 飞书上传 | `skill/scripts/upload_feishu.py` | 合并分析结果生成 Markdown 报告，上传至飞书云文档 Drive |
| 输出目录 | `output/` | 存放生成的学习报告（.md） |

**核心决策**：

1. **最小侵入**：新增模块完全不影响现有三个脚本，通过读取 JSON 文件解耦，无循环依赖
2. **三步容错加载**：三个输入文件（analysis / similar / review）各自独立加载，任一缺失不会阻塞——报告对应部分标注"未提供数据"即可继续
3. **飞书 API 双重容错**：接入层（获取 token）和上传层（上传文件）独立 try/except，失败时分别给出明确错误信息和修复建议
4. **--no-upload 模式**：支持仅生成本地 Markdown 报告不上传飞书，适配无飞书环境的开发和演示场景
5. **环境变量隔离**：飞书相关凭证（APP_ID / APP_SECRET / FOLDER_TOKEN）与 LLM 凭证完全分离

**修改文件（增量）**：

| 文件 | 修改内容 |
|------|----------|
| `skill/SKILL.md` | 版本升至 1.1.0，新增 upload_feishu.py 脚本定义、功能4输出 schema、飞书配置说明 |
| `README.md` | 项目简介加第4项功能，目录加 upload_feishu.py 和 output/，新增功能4使用文档和示例 |
| `iteration/iteration_log.md` | 本文档新增 v1.1.0 条目 |

**飞书 API 调用流程**：

```text
用户执行 upload_feishu.py
       │
       ▼
┌─────────────────────────────┐
│ 1. 加载 JSON 文件（容错）     │
│    analysis.json             │
│    similar_question.json     │
│    review_plan.json          │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 2. 合并生成 Markdown 报告    │
│    保存到 output/ 目录       │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 3. 获取 tenant_access_token  │
│    POST /auth/v3/...         │
│    使用 FEISHU_APP_ID +      │
│         FEISHU_APP_SECRET    │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 4. 上传文件到飞书 Drive      │
│    POST /drive/v1/files/     │
│         upload_all           │
│    返回 file_token + url     │
└─────────────────────────────┘
```

---

### v1.0.0 — 初始版本（2026-07-15）

**发布内容**：

| 模块 | 文件 | 说明 |
|------|------|------|
| Skill 定义 | `skill/SKILL.md` | 符合 WorkBuddy Skill 规范，含 YAML front matter |
| 错误分析 | `skill/scripts/analyze_error.py` | 调用 LLM 分析错误类型、原因、知识点 |
| 类似题生成 | `skill/scripts/generate_question.py` | 同知识点同难度出题，附答案和解题思路 |
| 复习计划 | `skill/scripts/review_plan.py` | 7 天分阶段复习方案 |
| 知识库 | `skill/references/error_types.md` | 六大类错误分类 + 9 个学科细分 |
| 知识库 | `skill/references/prompt_templates.md` | 三组 LLM Prompt 模板 |
| 测试数据 | `data/wrong_questions.json` | 9 条多学科多类型错题 |
| 测试记录 | `tests/test_record.md` | 环境、步骤、用例、结论 |
| 项目说明 | `README.md` | 安装、使用、设计亮点 |

**核心决策**：

1. **Prompt 与代码解耦**：将 Prompt 模板独立到 `references/prompt_templates.md`，方便非开发人员调优
2. **内置回退策略**：当 references 文件缺失时，脚本使用内置默认模板继续运行，不会因配置问题完全失效
3. **双格式输出**：每个脚本同时输出人类可读的控制台格式和标准 JSON，兼顾人工审核和程序对接
4. **可串联调用**：`--from-file` 参数支持直接将 `analyze_error.py` 的输出传给后续脚本

**已知限制**：

- 仅支持纯文本题目输入，不支持数学公式渲染和图片
- 无持久化存储，每次分析结果需手动保存
- 单用户模式，无学习进度追踪
- 不支持批量分析，需逐题手动输入

---

## 2. v1.0.0 迭代总结

### 2.1 完成度评估

| 需求 | 状态 |
|------|------|
| 错题原因分析 | ✅ 完成 |
| 生成类似练习题 | ✅ 完成 |
| 7天复习计划 | ✅ 完成 |
| 独立运行 | ✅ 全部支持 |
| 环境变量读取密钥 | ✅ 无硬编码 |
| 异常处理 | ✅ JSON/API/文件缺失全覆盖 |
| 中文注释 | ✅ 全部脚本 |
| 测试数据 | ✅ 9条，7学科，6类型 |

### 2.2 可优化项（已识别，待后续版本解决）

1. 批量分析模式（一次输入多道题）
2. 数学公式渲染支持（LaTeX → 图片）
3. 学生答题的流式分析（边写边诊断）
4. 错题本的导出功能（PDF/Word）

---

## 3. 项目级优化方案

以下四项方案旨在提升课程展示效果，展示本项目从"可用的工具"到"可落地的产品"的完整技术视野。

---

### 3.1 图片题 OCR 支持方案

#### 问题定义

当前 v1.0.0 仅支持文本输入，而学生错题最常见的输入形式是**拍照或截图**。需要打通"图片 → 文本 → 分析"的完整链路。

#### 技术方案

```
手机拍照 / 截图
      │
      ▼
┌─────────────────┐
│  图像预处理模块   │  ← OpenCV: 透视校正、去噪、二值化
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  OCR 识别引擎    │  ← 备选方案见下文
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  结构提取模块    │  ← 分离题干/选项/图表，识别学科
└────────┬────────┘
         │
         ▼
  现有 analyze_error.py
```

#### OCR 引擎选型对比

| 方案 | 优势 | 劣势 | 推荐场景 |
|------|------|------|----------|
| **PaddleOCR** | 中文识别率高、免费、离线 | 需 GPU 加速 | 数学/语文/英语题 |
| **Tesseract + chi_sim** | 轻量、开源 | 中文准确率一般 | 英语题、简单文本 |
| **GPT-4o Vision** | 理解上下文、可识图+分析一体 | 成本高、需网络 | 复杂图表题、手写题 |
| **腾讯云 OCR** | 高精度、含公式识别 | 需付费 | 正式产品化 |

**推荐组合**：PaddleOCR（文本） + GPT-4o Vision（含图表的复杂题）双引擎

#### 核心代码骨架

```python
# skill/scripts/ocr_pipeline.py (新增)

def ocr_pipeline(image_path: str, subject: str) -> dict:
    """
    图像预处理 + OCR 识别 + 结构提取
    返回标准化的错题输入格式
    """
    # 1. 图像预处理
    img = cv2.imread(image_path)
    img = correct_perspective(img)   # 透视校正
    img = denoise(img)                # 去噪

    # 2. OCR 识别
    text = paddleocr.ocr(img)         # PaddleOCR

    # 3. 结构提取（用 LLM 分离题干/选项/图表描述）
    structured = llm_extract_structure(text)

    # 4. 转换为标准输入格式
    return {
        "question_content": structured["stem"],
        "student_answer": structured["student_answer"],
        "correct_answer": structured["correct_answer"],
        "subject": subject,
    }
```

#### 新增文件

```
skill/scripts/ocr_pipeline.py          # OCR 主流程
skill/scripts/img_preprocess.py        # 图像预处理工具
skill/references/ocr_prompt.md         # OCR 结构提取 Prompt
```

#### 预估工作量

约 3-4 天（含模型调优）

---

### 3.2 知识图谱扩展方案

#### 问题定义

当前系统的知识点输出是**扁平列表**（如 `["二次函数", "顶点坐标", "配方法"]`），无法体现知识点之间的层级关系、前置依赖和横向关联。

#### 方案架构

```
                    ┌─────────────┐
                    │  二次函数    │ ← 一级节点
                    └──────┬──────┘
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ 顶点坐标  │ │ 图像性质  │ │ 一般式   │ ← 二级节点
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             │            │            │
        ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
        │ 配方法   │  │ 对称轴   │  │ 因式分解 │ ← 三级节点
        └─────────┘  └─────────┘  └─────────┘
```

#### 数据结构设计

```python
# skill/references/knowledge_graph.json (新增)

{
  "nodes": [
    {
      "id": "math_quadratic_function",
      "name": "二次函数",
      "subject": "数学",
      "grade": 9,
      "category": "函数",
      "difficulty": 3
    },
    {
      "id": "math_vertex_formula",
      "name": "顶点坐标公式",
      "subject": "数学",
      "grade": 9,
      "category": "函数",
      "difficulty": 2
    }
  ],
  "edges": [
    {
      "from": "math_quadratic_function",
      "to": "math_vertex_formula",
      "relation": "contains",
      "weight": 1.0
    },
    {
      "from": "math_vertex_formula",
      "to": "math_completing_square",
      "relation": "prerequisite",
      "weight": 0.8
    }
  ]
}
```

#### 核心能力

| 能力 | 说明 | 实现方式 |
|------|------|----------|
| **前置依赖查找** | 发现知识点 X 不会，定位到更基础的知识点 Y | 沿 `prerequisite` 边向上 BFS |
| **横向关联推荐** | 知识点 X 薄弱 → 也练练相关知识点 Z | 沿 `contains` 同父节点 |
| **漏洞影响分析** | 知识点 X 不懂 → 会影响后续哪些知识点 | 沿边向下 DFS |
| **图谱可视化** | 在浏览器中展示交互式知识图谱 | D3.js / ECharts |

#### 新增文件

```
skill/references/knowledge_graph.json     # 知识图谱数据
skill/scripts/knowledge_graph.py          # 图谱查询工具
skill/scripts/kg_visualizer.py            # 可视化导出
```

#### 初始数据覆盖

- 数学：9 年级 + 高一核心知识点（约 80 个节点，120 条边）
- 物理：力学 + 电学基础（约 40 个节点）
- 可随使用逐步扩展

#### 预估工作量

约 5-7 天（含数据构建）

---

### 3.3 飞书机器人接入方案

#### 问题定义

当前系统只能在命令行使用，不具备产品级交互体验。将 AI 错题教练接入飞书机器人，实现"拍照 → 发送 → 等分析 → 收到卡片"的用户闭环。

#### 方案架构

```
学生手机                       飞书服务器                   AI错题教练后端
   │                              │                              │
   │  📸 拍照，发到飞书群          │                              │
   │ ─────────────────────────>  │                              │
   │                              │  Webhook 推送消息事件        │
   │                              │ ──────────────────────────>  │
   │                              │                              │
   │                              │                     ┌────────▼────────┐
   │                              │                     │ Flask/FastAPI    │
   │                              │                     │ 1. 下载图片      │
   │                              │                     │ 2. OCR 识别      │
   │                              │                     │ 3. analyze_error │
   │                              │                     │ 4. 生成飞书卡片   │
   │                              │                     └────────┬────────┘
   │                              │                              │
   │                              │  <──── 回复交互式卡片 ─────  │
   │  <── 收到分析结果卡片 ───── │                              │
   │                              │                              │
   │  🖱️ 点击"生成类似题"按钮     │                              │
   │ ─────────────────────────>  │                              │
   │                              │    按钮回调事件               │
   │                              │ ──────────────────────────>  │
   │                              │                     generate_question.py
   │                              │                              │
   │  <── 收到练习题卡片 ─────── │  <── 回复新卡片 ────────── │
```

#### 飞书卡片设计

```json
{
  "config": { "wide_screen_mode": true },
  "header": {
    "title": { "tag": "plain_text", "content": "📊 AI错题教练 · 分析结果" },
    "template": "red"
  },
  "elements": [
    {
      "tag": "div",
      "text": { "tag": "lark_md", "content": "**错误类型**：概念混淆\n**错误原因**：..." }
    },
    {
      "tag": "action",
      "actions": [
        {
          "tag": "button",
          "text": { "tag": "plain_text", "content": "🔄 生成类似题" },
          "value": { "action": "generate_question", "data": {...} }
        },
        {
          "tag": "button",
          "text": { "tag": "plain_text", "content": "📅 生成复习计划" },
          "value": { "action": "review_plan", "data": {...} }
        }
      ]
    }
  ]
}
```

#### 部署方案

```
┌─────────────────────────────────────┐
│  方案A：轻量部署（开发/演示用）       │
│  ├── ngrok 内网穿透                  │
│  ├── Flask + 飞书事件订阅            │
│  └── SQLite 本地存储                 │
├─────────────────────────────────────┤
│  方案B：正式部署（生产环境）          │
│  ├── 腾讯云 / 阿里云 ECS             │
│  ├── Nginx + Gunicorn + Flask        │
│  ├── MySQL / PostgreSQL              │
│  └── 飞书应用商店上架                │
└─────────────────────────────────────┘
```

#### 新增文件

```
skill/feishu_bot/                     # 飞书机器人模块（新增目录）
├── app.py                            # Flask 主服务
├── card_builder.py                   # 飞书卡片构造器
├── event_handler.py                  # 事件回调处理
├── config.py                         # 飞书应用配置
└── requirements.txt                  # flask, lark-oapi 等依赖
```

#### 关键依赖

- `Flask` — Web 服务框架
- `lark-oapi` — 飞书开放平台 Python SDK
- `ngrok`（开发阶段）— 内网穿透

#### 预估工作量

约 5-6 天（含飞书应用审核）

---

### 3.4 多用户学习记录方案

#### 问题定义

当前系统无状态，每次分析都是"一次性"的。多用户场景下需要：
- 区分不同用户
- 存储历史分析记录
- 追踪知识点掌握变化
- 生成个人学习报告

#### 方案架构

```
┌──────────────────────────────────────────────────────┐
│                    API 层（FastAPI）                    │
│  POST /analyze     POST /users     GET /report/{uid}  │
└────────────────────────┬─────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────┐
│                    业务逻辑层                           │
│  analyze_error.py → generate_question.py → review_plan │
└────────────────────────┬─────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────┐
│                    数据存储层                           │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  用户表       │  │  错题记录表   │  │  掌握度表   │  │
│  │  users       │  │  error_logs  │  │  mastery    │  │
│  └──────────────┘  └──────────────┘  └────────────┘  │
│                         SQLite / PostgreSQL           │
└──────────────────────────────────────────────────────┘
```

#### 数据模型设计

```sql
-- 用户表
CREATE TABLE users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT NOT NULL,
    grade       TEXT,              -- 年级
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 错题记录表
CREATE TABLE error_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER REFERENCES users(id),
    subject         TEXT NOT NULL,
    question        TEXT NOT NULL,
    student_answer  TEXT NOT NULL,
    correct_answer  TEXT NOT NULL,
    error_type      TEXT NOT NULL,
    error_reason    TEXT,
    knowledge_points TEXT,         -- JSON 数组
    similar_question TEXT,         -- JSON（生成的类似题）
    review_plan     TEXT,          -- JSON（复习计划）
    image_url       TEXT,          -- 原始图片地址
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 知识点掌握度表
CREATE TABLE mastery (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER REFERENCES users(id),
    knowledge_point TEXT NOT NULL,
    error_count     INTEGER DEFAULT 0,
    reviewed_count  INTEGER DEFAULT 0,
    mastery_level   REAL DEFAULT 0.0,   -- 0.0-1.0 掌握程度
    last_reviewed   TIMESTAMP,
    UNIQUE(user_id, knowledge_point)
);
```

#### 学习报告示例

```
┌─────────────────────────────────────────┐
│         📊 张三 · 数学学习周报            │
│         2026-07-08 ~ 2026-07-15          │
├─────────────────────────────────────────┤
│                                         │
│  本周错题数：12 道                        │
│  已掌握知识点：3 个  ← 较上周 +1          │
│  薄弱知识点：2 个                         │
│                                         │
│  🔴 需重点关注：                          │
│  · 二次函数顶点公式（错 4 次）             │
│  · 绝对值不等式（错 3 次）                 │
│                                         │
│  📈 掌握度变化：                          │
│  ████████░░ 一元二次方程  80% ↑          │
│  ██████░░░░ 因式分解      60% →          │
│  ███░░░░░░░ 二次函数      30% ↓          │
│                                         │
│  💡 建议：本周集中复习二次函数，            │
│     避免影响下周的"抛物线"章节学习          │
│                                         │
└─────────────────────────────────────────┘
```

#### 新增文件

```
skill/scripts/db_manager.py           # 数据库管理工具
skill/scripts/report_generator.py     # 学习报告生成器
skill/references/report_template.md   # 报告模板
skill/api_server.py                   # FastAPI 服务（可选）
```

#### 预估工作量

约 4-5 天

---

## 4. 版本路线图

```
v1.0.0 (当前)          v1.1.0 (当前)           v1.2.0                v2.0.0
    │                     │                     │                     │
    ▼                     ▼                     ▼                     ▼
┌─────────┐        ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│ 核心三   │   →   │ + 飞书上传   │   →   │ + 知识图谱   │   →   │ + 飞书机器人 │
│ 大功能   │        │              │       │ + 学习报告   │       │ + 完整产品化 │
└─────────┘        └─────────────┘       └─────────────┘       └─────────────┘
  2026.07              2026.07               2026.08               2026.09
```

---

## 5. 变更记录

| 日期 | 版本 | 变更内容 | 作者 |
|------|------|----------|------|
| 2026-07-16 | v1.1.0 | 新增 upload_feishu.py：学习报告导出 + 飞书云文档上传，更新 SKILL.md / README | 课程项目组 |
| 2026-07-15 | v1.0.0 | 初始版本发布：三大核心功能、测试数据、文档 | 课程项目组 |
| 2026-07-15 | v1.0.0 | 补充四项项目级优化方案（OCR/知识图谱/飞书/多用户） | 课程项目组 |
