#!/usr/bin/env python3
"""
review_plan.py — 7天复习计划生成脚本

功能：
    根据学生的错题分析结果（错误类型、涉及知识点、学科），
    调用 OpenAI API 生成一份 7 天分阶段复习计划，
    包括每天的具体任务、复习知识点总数和预估总时长。

运行方式：
    python review_plan.py \\
        --error_type "概念混淆" \\
        --knowledge_points "二次函数,顶点坐标,配方法" \\
        --subject "数学"

    也可以从 JSON 文件读取（由 analyze_error.py 输出的分析结果）：
    python review_plan.py --from-file analysis_result.json

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
        "temperature": float(os.environ.get("OPENAI_TEMPERATURE", "0.3")),
    }


# ============================================================
# 加载 Prompt 模板
# ============================================================

def load_prompt_template() -> dict:
    """
    从 references/prompt_templates.md 加载模板3（复习计划）。
    使用正则匹配第三个 System Prompt / User Prompt 对。
    """
    ref_dir = Path(__file__).resolve().parent.parent / "references"
    file_path = ref_dir / "prompt_templates.md"
    if not file_path.exists():
        return _get_fallback_prompt()

    content = file_path.read_text(encoding="utf-8")

    # 匹配模板3（7天复习计划）所在段落
    section = re.search(
        r"## 模板\d[：:]7天复习计划.*?(?=## 模板|\Z)",
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
    """内置后备复习计划模板。"""
    return {
        "system_prompt": (
            "你是{subject}学科的学习规划师。学生的错误类型是 {error_type}，"
            "薄弱知识点：{knowledge_points}。"
            "请制定7天复习计划，每天包含具体任务。"
            "请以 JSON 格式输出："
            '{{"plan": {{"day_1": "...", ..., "day_7": "..."}}, '
            '"total_review_items": 数字, "estimated_hours": 数字}}'
        ),
        "user_prompt": (
            "【学科】{subject}\n"
            "【错误类型】{error_type}\n"
            "【知识点】{knowledge_points}\n"
            "请制定7天复习计划。"
        ),
    }


# ============================================================
# 核心功能：调用 LLM 生成 7 天复习计划
# ============================================================

def generate_review_plan(
    error_type: str,
    knowledge_points: str,
    subject: str,
    config: dict,
    prompt_templates: dict,
) -> dict:
    """
    调用 OpenAI API 生成 7 天复习计划。

    参数：
        error_type:       错误类型
        knowledge_points: 涉及的知识点（逗号分隔）
        subject:          学科
        config:           API 配置
        prompt_templates: Prompt 模板

    返回：
        包含 plan（7天任务）、total_review_items、estimated_hours 的字典
    """
    system_prompt = prompt_templates["system_prompt"].format(
        subject=subject,
        error_type=error_type,
        knowledge_points=knowledge_points,
    )
    user_prompt = prompt_templates["user_prompt"].format(
        subject=subject,
        error_type=error_type,
        knowledge_points=knowledge_points,
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
            "plan": {"day_1": f"解析失败：{content[:100]}"},
            "total_review_items": 0,
            "estimated_hours": 0,
        }
    except Exception as e:
        print(f"❌ API 调用失败：{e}")
        return {
            "plan": {"day_1": f"调用失败：{str(e)}"},
            "total_review_items": 0,
            "estimated_hours": 0,
        }


# ============================================================
# 格式化输出
# ============================================================

def print_review_plan(result: dict, subject: str, error_type: str, knowledge_points: str):
    """美化打印复习计划。"""
    print("=" * 55)
    print("📅 7 天复习计划")
    print("=" * 55)
    print(f"学科：{subject}")
    print(f"错误类型：{error_type}")
    print(f"薄弱知识点：{knowledge_points}")
    print(f"复习知识点数：{result.get('total_review_items', 0)}")
    print(f"预估总时长：{result.get('estimated_hours', 0)} 小时")
    print("-" * 55)

    plan = result.get("plan", {})
    for day_key in [f"day_{i}" for i in range(1, 8)]:
        task = plan.get(day_key, "—")
        day_label = day_key.replace("day_", "第") + "天"
        print(f"  {day_label}：{task}")

    print("=" * 55)


# ============================================================
# 命令行入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="AI 错题教练 — 生成 7 天复习计划",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python review_plan.py \\
      --error_type "概念混淆" \\
      --knowledge_points "二次函数,顶点坐标,配方法" \\
      --subject "数学"

  python review_plan.py --from-file analysis_result.json
        """,
    )
    parser.add_argument(
        "--error_type", "-e",
        default="概念混淆",
        help="错误类型（默认: 概念混淆）",
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
        "--from-file", "-f",
        default="",
        help="从 JSON 文件读取分析结果（由 analyze_error.py 输出）",
    )

    args = parser.parse_args()

    # 从文件或命令行参数获取输入
    if args.from_file:
        try:
            with open(args.from_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            knowledge_points = ", ".join(data.get("knowledge_points", []))
            error_type = data.get("error_type", args.error_type)
            subject = data.get("subject", args.subject)
            if not knowledge_points:
                print("❌ 文件中的 knowledge_points 为空，无法生成复习计划")
                sys.exit(1)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"❌ 读取文件失败：{e}")
            sys.exit(1)
    else:
        error_type = args.error_type
        knowledge_points = args.knowledge_points
        subject = args.subject

    if not knowledge_points:
        print("❌ 错误：必须提供 --knowledge_points 或 --from-file 参数")
        sys.exit(1)

    # 加载配置和模板
    config = load_config()
    prompt_templates = load_prompt_template()

    # 生成复习计划
    print("📅 正在生成 7 天复习计划...\n")
    result = generate_review_plan(
        error_type=error_type,
        knowledge_points=knowledge_points,
        subject=subject,
        config=config,
        prompt_templates=prompt_templates,
    )

    # 美化输出
    print_review_plan(result, subject, error_type, knowledge_points)

    # JSON 输出
    print("\n📋 JSON 输出（供程序对接）：")
    output = {
        "subject": subject,
        "error_type": error_type,
        "knowledge_points": knowledge_points,
        **result,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
