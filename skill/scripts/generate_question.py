#!/usr/bin/env python3
"""
generate_question.py — 生成类似练习题脚本

功能：
    根据学生的错题分析结果（涉及知识点、错误类型、学科），
    调用 OpenAI API 生成一道考察同一知识点、难度相近的练习题，
    附带正确答案和解题思路。

运行方式：
    python generate_question.py \\
        --knowledge_points "二次函数,顶点坐标,配方法" \\
        --subject "数学" \\
        --error_type "概念混淆"

    也可从 JSON 文件读取（已由 analyze_error.py 分析的结果）：
    python generate_question.py \\
        --from-file analysis_result.json

环境变量：
    OPENAI_API_KEY      必填，OpenAI API 密钥
    OPENAI_BASE_URL     可选，API 基础地址（默认 https://api.openai.com/v1）
    OPENAI_MODEL        可选，模型名称（默认 gpt-4o）
    OPENAI_TEMPERATURE  可选，温度参数（默认 0.5，略高以增加出题多样性）
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

from openai import OpenAI


# ============================================================
# 配置加载
# ============================================================

def load_config() -> dict:
    """从环境变量加载 API 配置。"""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("❌ 错误：未设置环境变量 OPENAI_API_KEY")
        print("   请运行: export OPENAI_API_KEY='sk-xxx'")
        sys.exit(1)

    return {
        "api_key": api_key,
        "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o"),
        # 出题时适当提高 temperature 以增加题目多样性
        "temperature": float(os.environ.get("OPENAI_TEMPERATURE", "0.5")),
    }


# ============================================================
# 加载 Prompt 模板
# ============================================================

def load_prompt_template() -> dict:
    """
    从 references/prompt_templates.md 加载模板2（生成类似题）。
    使用正则匹配第二个 System Prompt / User Prompt 对。
    """
    ref_dir = Path(__file__).resolve().parent.parent / "references"
    file_path = ref_dir / "prompt_templates.md"
    if not file_path.exists():
        return _get_fallback_prompt()

    content = file_path.read_text(encoding="utf-8")

    # 匹配模板2的标记行到下一个模板标记行之间的所有 System Prompt 和 User Prompt
    section = re.search(
        r"## 模板\d[：:]生成类似题.*?(?=## 模板|\Z)",
        content,
        re.DOTALL,
    )
    if not section:
        return _get_fallback_prompt()

    section_text = section.group(0)

    sys_match = re.search(
        r"### System Prompt\n+```\n(.*?)```",
        section_text,
        re.DOTALL,
    )
    usr_match = re.search(
        r"### User Prompt\n+```\n(.*?)```",
        section_text,
        re.DOTALL,
    )

    if sys_match and usr_match:
        return {
            "system_prompt": sys_match.group(1).strip(),
            "user_prompt": usr_match.group(1).strip(),
        }
    return _get_fallback_prompt()


def _get_fallback_prompt() -> dict:
    """内置后备出题模板。"""
    return {
        "system_prompt": (
            "你是{subject}学科的出题教师。请针对知识点 {knowledge_points} "
            "生成一道难度中等的练习题。"
            "请以 JSON 格式输出："
            '{{"question": "...", "answer": "...", "explanation": "..."}}'
        ),
        "user_prompt": (
            "【学科】{subject}\n"
            "【知识点】{knowledge_points}\n"
            "【错误类型】{error_type}\n"
            "请生成一道类似题。"
        ),
    }


# ============================================================
# 核心功能：调用 LLM 生成类似题
# ============================================================

def generate_question(
    knowledge_points: str,
    subject: str,
    error_type: str,
    config: dict,
    prompt_templates: dict,
) -> dict:
    """
    调用 OpenAI API 生成类似练习题。

    参数：
        knowledge_points: 涉及的知识点（逗号分隔的字符串）
        subject:          学科
        error_type:       错误类型
        config:           API 配置
        prompt_templates: Prompt 模板

    返回：
        包含 question, answer, explanation 的字典
    """
    system_prompt = prompt_templates["system_prompt"].format(
        subject=subject,
        knowledge_points=knowledge_points,
    )
    user_prompt = prompt_templates["user_prompt"].format(
        subject=subject,
        knowledge_points=knowledge_points,
        error_type=error_type,
    )

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

        # 提取 JSON
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
        if json_match:
            content = json_match.group(1).strip()

        result = json.loads(content)
        return result

    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败：{e}")
        return {
            "question": "生成失败",
            "answer": "—",
            "explanation": f"LLM 输出格式异常：{content[:200]}",
        }
    except Exception as e:
        print(f"❌ API 调用失败：{e}")
        return {
            "question": "生成失败",
            "answer": "—",
            "explanation": str(e),
        }


# ============================================================
# 命令行入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="AI 错题教练 — 生成类似练习题",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python generate_question.py \\
      --knowledge_points "二次函数,顶点坐标,配方法" \\
      --subject "数学" \\
      --error_type "概念混淆"

  python generate_question.py --from-file analysis_result.json
        """,
    )
    parser.add_argument(
        "--knowledge_points", "-k",
        default="",
        help="涉及的知识点，多个用逗号分隔",
    )
    parser.add_argument(
        "--subject", "-j",
        default="数学",
        choices=["数学", "语文", "英语", "物理", "化学", "生物", "历史", "地理", "政治", "其他"],
        help="所属学科（默认: 数学）",
    )
    parser.add_argument(
        "--error_type", "-e",
        default="概念混淆",
        help="错误类型（默认: 概念混淆）",
    )
    parser.add_argument(
        "--from-file", "-f",
        default="",
        help="从 JSON 文件读取分析结果（由 analyze_error.py 输出）",
    )

    args = parser.parse_args()

    # 如果指定了 --from-file，从文件读取参数
    if args.from_file:
        try:
            with open(args.from_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            knowledge_points = ", ".join(data.get("knowledge_points", []))
            subject = data.get("subject", args.subject)
            error_type = data.get("error_type", args.error_type)
            if not knowledge_points:
                print("❌ 文件中的 knowledge_points 为空，无法生成题目")
                sys.exit(1)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"❌ 读取文件失败：{e}")
            sys.exit(1)
    else:
        knowledge_points = args.knowledge_points
        subject = args.subject
        error_type = args.error_type

    if not knowledge_points:
        print("❌ 错误：必须提供 --knowledge_points 或 --from-file 参数")
        sys.exit(1)

    # 加载配置和模板
    config = load_config()
    prompt_templates = load_prompt_template()

    # 生成类似题
    print(f"📝 正在为知识点「{knowledge_points}」生成类似题...\n")
    result = generate_question(
        knowledge_points=knowledge_points,
        subject=subject,
        error_type=error_type,
        config=config,
        prompt_templates=prompt_templates,
    )

    # 输出结果
    print("=" * 50)
    print("📝 类似练习题")
    print("=" * 50)
    print(f"学科：{subject}")
    print(f"考查知识点：{knowledge_points}")
    print(f"针对错误类型：{error_type}")
    print("-" * 50)
    print(f"【题目】\n{result.get('question', '—')}")
    print()
    print(f"【答案】\n{result.get('answer', '—')}")
    print()
    print(f"【解题思路】\n{result.get('explanation', '—')}")
    print("=" * 50)

    # JSON 输出
    print("\n📋 JSON 输出（供程序对接）：")
    output = {
        "knowledge_points": knowledge_points,
        "subject": subject,
        "error_type": error_type,
        **result,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
