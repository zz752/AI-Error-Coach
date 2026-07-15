#!/usr/bin/env python3
"""
analyze_error.py — 错题原因分析脚本

功能：
    接收错题的题干、学生答案、正确答案和学科信息，
    调用 OpenAI API 分析错误类型、错误原因和涉及的知识点。

运行方式：
    python analyze_error.py \\
        --question "已知函数 f(x)=x²-4x+3，求 f(x) 的最小值" \\
        --student_answer "3" \\
        --correct_answer "-1" \\
        --subject "数学"

环境变量：
    OPENAI_API_KEY      必填，OpenAI API 密钥
    OPENAI_BASE_URL     可选，API 基础地址（默认 https://api.openai.com/v1）
    OPENAI_MODEL        可选，模型名称（默认 gpt-4o）
    OPENAI_TEMPERATURE  可选，温度参数（默认 0.3）
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

from openai import OpenAI


# ============================================================
# 配置：从环境变量读取，不硬编码任何密钥
# ============================================================

def load_config() -> dict:
    """加载配置：从环境变量读取 API 密钥等参数。"""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("❌ 错误：未设置环境变量 OPENAI_API_KEY")
        print("   请运行: export OPENAI_API_KEY='sk-xxx'")
        sys.exit(1)

    return {
        "api_key": api_key,
        "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o"),
        "temperature": float(os.environ.get("OPENAI_TEMPERATURE", "0.3")),
    }


# ============================================================
# 加载 references 目录下的知识文件
# ============================================================

def load_error_types() -> str:
    """从 references/error_types.md 加载错误类型分类体系。"""
    ref_dir = Path(__file__).resolve().parent.parent / "references"
    file_path = ref_dir / "error_types.md"
    if file_path.exists():
        return file_path.read_text(encoding="utf-8")
    else:
        print(f"⚠️  警告：未找到 {file_path}，使用内置默认分类")
        return "概念混淆 | 计算失误 | 审题偏差 | 知识盲区 | 逻辑推理错误 | 解题策略不当"


def load_prompt_template() -> dict:
    """
    从 references/prompt_templates.md 加载 Prompt 模板。
    返回包含 system_prompt 和 user_prompt 的字典。
    """
    ref_dir = Path(__file__).resolve().parent.parent / "references"
    file_path = ref_dir / "prompt_templates.md"
    if not file_path.exists():
        print(f"⚠️  警告：未找到 {file_path}，使用内置默认模板")
        return _get_fallback_prompt()

    content = file_path.read_text(encoding="utf-8")

    # 提取模板1（错题原因分析）的 System Prompt
    sys_match = re.search(
        r"### System Prompt\n+```\n(.*?)```",
        content,
        re.DOTALL,
    )
    # 提取模板1的 User Prompt
    usr_match = re.search(
        r"### User Prompt\n+```\n(.*?)```",
        content,
        re.DOTALL,
    )

    if sys_match and usr_match:
        return {
            "system_prompt": sys_match.group(1).strip(),
            "user_prompt": usr_match.group(1).strip(),
        }
    else:
        print("⚠️  警告：无法解析模板文件，使用内置默认模板")
        return _get_fallback_prompt()


def _get_fallback_prompt() -> dict:
    """内置后备模板，防止 references 文件缺失时脚本无法运行。"""
    return {
        "system_prompt": (
            "你是一位经验丰富的{subject}学科教师。"
            "请根据以下错误类型分类分析学生的错题：{error_types_catalog}\n"
            "请以 JSON 格式输出："
            '{{"error_type": "...", "error_reason": "...", "knowledge_points": [...]}}'
        ),
        "user_prompt": (
            "【学科】{subject}\n"
            "【题目】{question_content}\n"
            "【学生答案】{student_answer}\n"
            "【正确答案】{correct_answer}\n"
            "请输出 JSON 格式分析结果。"
        ),
    }


# ============================================================
# 核心功能：调用 LLM 分析错题
# ============================================================

def analyze_error(
    question_content: str,
    student_answer: str,
    correct_answer: str,
    subject: str,
    config: dict,
    prompt_templates: dict,
    error_types_catalog: str,
) -> dict:
    """
    调用 OpenAI API 分析错题的错误原因。

    参数：
        question_content: 题目题干
        student_answer:   学生的错误答案
        correct_answer:   正确答案
        subject:          学科（如"数学"）
        config:           API 配置字典
        prompt_templates: Prompt 模板字典
        error_types_catalog: 错误类型分类体系

    返回：
        包含 error_type, error_reason, knowledge_points 的字典
    """
    # 构造 Prompt：将占位符替换为实际内容
    system_prompt = prompt_templates["system_prompt"].format(
        subject=subject,
        error_types_catalog=error_types_catalog,
    )
    user_prompt = prompt_templates["user_prompt"].format(
        subject=subject,
        question_content=question_content,
        student_answer=student_answer,
        correct_answer=correct_answer,
    )

    # 初始化 OpenAI 客户端
    client = OpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"],
    )

    try:
        response = client.chat.completions.create(
            model=config["model"],
            temperature=config["temperature"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content or "{}"

        # 尝试提取 JSON（LLM 可能输出包裹在 ```json ... ``` 中）
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
        if json_match:
            content = json_match.group(1).strip()

        result = json.loads(content)
        return result

    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败：{e}")
        print(f"   LLM 原始输出：{content[:500]}")
        return {
            "error_type": "解析失败",
            "error_reason": f"LLM 返回格式异常：{content[:200]}",
            "knowledge_points": [],
        }
    except Exception as e:
        print(f"❌ API 调用失败：{e}")
        return {
            "error_type": "调用失败",
            "error_reason": str(e),
            "knowledge_points": [],
        }


# ============================================================
# 命令行入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="AI 错题教练 — 错题原因分析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python analyze_error.py \\
      --question "已知 f(x)=x²-4x+3，求最小值" \\
      --student_answer "3" \\
      --correct_answer "-1" \\
      --subject "数学"
        """,
    )
    parser.add_argument(
        "--question", "-q",
        required=True,
        help="错题的完整题干",
    )
    parser.add_argument(
        "--student_answer", "-s",
        required=True,
        help="学生给出的错误答案",
    )
    parser.add_argument(
        "--correct_answer", "-c",
        required=True,
        help="正确答案",
    )
    parser.add_argument(
        "--subject", "-j",
        required=True,
        choices=["数学", "语文", "英语", "物理", "化学", "生物", "历史", "地理", "政治", "其他"],
        help="所属学科",
    )

    args = parser.parse_args()

    # 1. 加载配置
    config = load_config()

    # 2. 加载知识文件
    error_types_catalog = load_error_types()
    prompt_templates = load_prompt_template()

    # 3. 调用 LLM 分析
    print("🔍 正在分析错题原因...\n")
    result = analyze_error(
        question_content=args.question,
        student_answer=args.student_answer,
        correct_answer=args.correct_answer,
        subject=args.subject,
        config=config,
        prompt_templates=prompt_templates,
        error_types_catalog=error_types_catalog,
    )

    # 4. 输出结果
    print("=" * 50)
    print("📊 分析结果")
    print("=" * 50)
    print(f"学科：{args.subject}")
    print(f"错误类型：{result.get('error_type', '未知')}")
    print(f"错误原因：{result.get('error_reason', '未知')}")
    knowledge_points = result.get("knowledge_points", [])
    print(f"涉及知识点：{'、'.join(knowledge_points) if knowledge_points else '无'}")
    print("=" * 50)

    # 同时输出标准 JSON（方便被其他程序调用）
    print("\n📋 JSON 输出（供程序对接）：")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
