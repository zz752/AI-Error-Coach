#!/usr/bin/env python3
"""
upload_feishu.py — 学习报告导出与飞书上传脚本

功能：
    读取前三步的分析结果（analysis.json / similar_question.json / review_plan.json），
    合并生成一份 Markdown 学习报告，保存到 output/ 目录，
    然后调用飞书开放平台 API 上传至飞书云文档 Drive，
    返回 file_token 和 document_url。

运行方式：
    # 方式A：指定三个 JSON 文件路径
    python skill/scripts/upload_feishu.py \
        --analysis output/analysis.json \
        --similar output/similar_question.json \
        --review output/review_plan.json

    # 方式B：指定 output 目录（自动匹配文件名）
    python skill/scripts/upload_feishu.py --output-dir output/

环境变量：
    FEISHU_APP_ID          必填，飞书应用的 App ID
    FEISHU_APP_SECRET      必填，飞书应用的 App Secret
    FEISHU_FOLDER_TOKEN    可选，上传目标文件夹的 folder_token（不填则上传到飞书云文档根目录）

飞书 API 参考：
    - 获取 tenant_access_token:
      POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal
    - 上传文件到云文档:
      POST https://open.feishu.cn/open-apis/drive/v1/files/upload_all
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests


# ============================================================
# 配置：从环境变量读取，不硬编码任何密钥
# ============================================================

def load_config() -> dict:
    """从环境变量加载飞书应用配置。"""
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")

    if not app_id or not app_secret:
        print("❌ 错误：未设置飞书应用凭证")
        print("   请设置以下环境变量：")
        print("   export FEISHU_APP_ID='cli_xxxxxxxxxxxx'")
        print("   export FEISHU_APP_SECRET='xxxxxxxxxxxxxxxxxxxxxxxxxx'")
        sys.exit(1)

    return {
        "app_id": app_id,
        "app_secret": app_secret,
        "folder_token": os.environ.get("FEISHU_FOLDER_TOKEN", ""),
        "base_url": "https://open.feishu.cn/open-apis",
    }


# ============================================================
# 飞书 API 对接
# ============================================================

def get_tenant_access_token(config: dict) -> str:
    """
    获取飞书 tenant_access_token。
    文档：https://open.feishu.cn/document/server-docs/authentication-management/access-token/tenant_access_token_internal

    返回：
        access_token 字符串
    """
    url = f"{config['base_url']}/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": config["app_id"],
        "app_secret": config["app_secret"],
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 0:
            print(f"❌ 获取飞书 access_token 失败：{data.get('msg', '未知错误')}")
            print(f"   错误码：{data.get('code')}")
            sys.exit(1)

        return data["tenant_access_token"]

    except requests.exceptions.Timeout:
        print("❌ 获取飞书 access_token 超时，请检查网络连接")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接飞书 API，请检查网络和 DNS")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ 获取飞书 access_token 请求异常：{e}")
        sys.exit(1)


def upload_to_feishu_drive(
    access_token: str,
    file_path: str,
    file_name: str,
    folder_token: str,
    config: dict,
) -> dict:
    """
    上传文件到飞书云文档 Drive。
    文档：https://open.feishu.cn/document/server-docs/docs/drive-v1/file/upload_all

    参数：
        access_token:  飞书 tenant_access_token
        file_path:     本地文件绝对路径
        file_name:     上传后显示的文件名
        folder_token:  目标文件夹 token（空字符串表示根目录）
        config:        配置字典

    返回：
        {"file_token": "...", "url": "..."}
    """
    url = f"{config['base_url']}/drive/v1/files/upload_all"

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    # 飞书上传 API 使用 multipart/form-data
    with open(file_path, "rb") as f:
        files = {
            "file": (file_name, f, "application/octet-stream"),
        }
        data = {
            "file_name": file_name,
            "parent_type": "explorer",
            "parent_node": folder_token,
            "size": str(os.path.getsize(file_path)),
        }

        try:
            resp = requests.post(
                url,
                headers=headers,
                files=files,
                data=data,
                timeout=60,  # 上传大文件可能需要更长时间
            )
            resp.raise_for_status()
            result = resp.json()

            if result.get("code") != 0:
                print(f"❌ 上传飞书云文档失败：{result.get('msg', '未知错误')}")
                print(f"   错误码：{result.get('code')}")
                return {"file_token": "", "url": ""}

            file_token = result.get("data", {}).get("file_token", "")
            file_url = result.get("data", {}).get("url", "")

            return {"file_token": file_token, "url": file_url}

        except requests.exceptions.Timeout:
            print("❌ 上传文件超时（60秒），文件可能较大，请稍后重试")
            return {"file_token": "", "url": ""}
        except requests.exceptions.ConnectionError:
            print("❌ 上传过程中网络连接断开")
            return {"file_token": "", "url": ""}
        except requests.exceptions.RequestException as e:
            print(f"❌ 上传文件请求异常：{e}")
            return {"file_token": "", "url": ""}


# ============================================================
# 报告生成
# ============================================================

def load_json(file_path: str) -> dict:
    """
    安全加载 JSON 文件，文件不存在时返回空字典。

    参数：
        file_path: JSON 文件路径

    返回：
        解析后的字典，加载失败返回 {}
    """
    path = Path(file_path)
    if not path.exists():
        print(f"⚠️  警告：文件 {file_path} 不存在，对应内容将留空")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"⚠️  警告：文件 {file_path} JSON 解析失败：{e}")
        return {}


def generate_markdown_report(
    analysis: dict,
    similar: dict,
    review: dict,
    subject: str = "",
) -> str:
    """
    将三个分析结果合并为一份完整的 Markdown 学习报告。

    参数：
        analysis: 错题分析结果（analyze_error.py 输出）
        similar:  类似题生成结果（generate_question.py 输出）
        review:   复习计划结果（review_plan.py 输出）
        subject:  学科（优先从 analysis 中提取）

    返回：
        Markdown 格式的完整报告字符串
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    subject = subject or analysis.get("subject", analysis.get("学科", "未知学科"))

    lines = []

    # ── 报告头部 ──
    lines.append(f"# 📊 AI错题教练 · 学习报告")
    lines.append(f"")
    lines.append(f"> 生成时间：{now}")
    lines.append(f"> 学科：{subject}")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # ── 第一部分：错题分析 ──
    lines.append(f"## 一、错题原因分析")
    lines.append(f"")
    if analysis:
        error_type = analysis.get("error_type", "—")
        error_reason = analysis.get("error_reason", "—")
        knowledge_points = analysis.get("knowledge_points", [])

        lines.append(f"| 项目 | 内容 |")
        lines.append(f"|------|------|")
        lines.append(f"| **错误类型** | {error_type} |")
        lines.append(f"| **错误原因** | {error_reason} |")
        kp_str = "、".join(knowledge_points) if knowledge_points else "—"
        lines.append(f"| **涉及知识点** | {kp_str} |")
    else:
        lines.append(f"> ⚠️ 未提供错题分析数据")
    lines.append(f"")

    # ── 第二部分：类似练习题 ──
    lines.append(f"## 二、类似练习题")
    lines.append(f"")
    if similar:
        question = similar.get("question", "—")
        answer = similar.get("answer", "—")
        explanation = similar.get("explanation", "—")

        lines.append(f"### 📝 题目")
        lines.append(f"")
        lines.append(f"{question}")
        lines.append(f"")
        lines.append(f"### ✅ 答案")
        lines.append(f"")
        lines.append(f"{answer}")
        lines.append(f"")
        lines.append(f"### 💡 解题思路")
        lines.append(f"")
        lines.append(f"{explanation}")
    else:
        lines.append(f"> ⚠️ 未提供类似练习题数据")
    lines.append(f"")

    # ── 第三部分：7天复习计划 ──
    lines.append(f"## 三、7 天复习计划")
    lines.append(f"")
    if review:
        total_items = review.get("total_review_items", 0)
        estimated_hours = review.get("estimated_hours", 0)
        plan = review.get("plan", {})

        lines.append(f"- **复习知识点数**：{total_items} 个")
        lines.append(f"- **预估总时长**：{estimated_hours} 小时")
        lines.append(f"")

        lines.append(f"| 日期 | 学习任务 |")
        lines.append(f"|------|----------|")
        for i in range(1, 8):
            day_key = f"day_{i}"
            task = plan.get(day_key, "—")
            lines.append(f"| 第{i}天 | {task} |")
    else:
        lines.append(f"> ⚠️ 未提供复习计划数据")
    lines.append(f"")

    # ── 尾部 ──
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"*本报告由 AI错题教练 Skill 自动生成*")

    return "\n".join(lines)


def save_report(markdown_content: str, output_dir: str) -> str:
    """
    保存 Markdown 报告到 output/ 目录。

    参数：
        markdown_content: Markdown 文本
        output_dir:       输出目录路径

    返回：
        保存的文件完整路径
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"learning_report_{timestamp}.md"
    file_path = out_path / file_name

    file_path.write_text(markdown_content, encoding="utf-8")
    return str(file_path.resolve())


# ============================================================
# 命令行入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="AI 错题教练 — 学习报告导出与飞书上传",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 指定三个 JSON 文件
  python skill/scripts/upload_feishu.py \\
      --analysis output/analysis.json \\
      --similar output/similar_question.json \\
      --review output/review_plan.json

  # 指定 output 目录（自动匹配文件名）
  python skill/scripts/upload_feishu.py --output-dir output/

  # 仅生成报告不上传飞书
  python skill/scripts/upload_feishu.py \\
      --analysis output/analysis.json \\
      --review output/review_plan.json \\
      --no-upload

环境变量（飞书上传必需）：
  export FEISHU_APP_ID="cli_xxxxxxxxxxxx"
  export FEISHU_APP_SECRET="xxxxxxxxxxxxxxxxxxxxxxxxxx"
  export FEISHU_FOLDER_TOKEN="xxxxx"    # 可选，上传目标文件夹
        """,
    )
    parser.add_argument(
        "--analysis", "-a",
        default="",
        help="错题分析结果 JSON 文件路径（analyze_error.py 输出）",
    )
    parser.add_argument(
        "--similar", "-s",
        default="",
        help="类似题结果 JSON 文件路径（generate_question.py 输出）",
    )
    parser.add_argument(
        "--review", "-r",
        default="",
        help="复习计划结果 JSON 文件路径（review_plan.py 输出）",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="",
        help="output 目录路径，自动匹配分析/类似题/复习计划 JSON 文件",
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="仅生成本地报告，不上传飞书",
    )
    parser.add_argument(
        "--subject",
        default="",
        help="学科名称（可选，优先从 analysis 中提取）",
    )

    args = parser.parse_args()

    # ── 第1步：确定文件路径 ──
    if args.output_dir:
        out_dir = Path(args.output_dir)
        analysis_path = out_dir / "analysis.json"
        similar_path = out_dir / "similar_question.json"
        review_path = out_dir / "review_plan.json"

        # 兼容：output_dir 下可能直接放了相关 JSON
        # 若默认文件名不存在，尝试在 output_dir 下查找匹配文件
        if not analysis_path.exists():
            analysis_path = Path(args.output_dir)

        analysis_file = str(analysis_path) if analysis_path.exists() else ""
        similar_file = str(similar_path) if similar_path.exists() else ""
        review_file = str(review_path) if review_path.exists() else ""
    else:
        analysis_file = args.analysis
        similar_file = args.similar
        review_file = args.review

    # 必须至少提供 analysis 或 review
    if not analysis_file and not review_file:
        print("❌ 错误：必须提供 --analysis 或 --review（或 --output-dir）")
        print("   示例：python upload_feishu.py --output-dir output/")
        sys.exit(1)

    # ── 第2步：加载 JSON 数据 ──
    print("📄 正在加载分析数据...")
    analysis = load_json(analysis_file) if analysis_file else {}
    similar = load_json(similar_file) if similar_file else {}
    review = load_json(review_file) if review_file else {}

    total_sources = sum(1 for d in [analysis, similar, review] if d)
    print(f"   已加载 {total_sources}/3 份数据" + (" (部分缺失，报告将标注)" if total_sources < 3 else ""))

    # ── 第3步：生成 Markdown 报告 ──
    print("📝 正在生成学习报告...")
    subject = args.subject or analysis.get("subject", "")
    markdown = generate_markdown_report(analysis, similar, review, subject)

    # 确定输出目录
    project_root = Path(__file__).resolve().parent.parent.parent
    output_dir = str(project_root / "output")

    file_path = save_report(markdown, output_dir)
    file_name = Path(file_path).name
    print(f"   报告已保存：{file_path}")

    # ── 第4步：上传飞书（可选） ──
    if args.no_upload:
        print("\n⏭️  已跳过飞书上��（--no-upload）")
        print("=" * 55)
        print("✅ 本地报告生成完成！")
        print(f"   📁 {file_path}")
        print("=" * 55)
        return

    print("\n☁️  正在上传至飞书云文档...")

    # 加载飞书配置
    config = load_config()

    # 获取 access_token
    print("   1/3 获取飞书访问令牌...")
    access_token = get_tenant_access_token(config)
    print("   ✅ 令牌获取成功")

    # 上传文件
    print("   2/3 上传文件...")
    upload_result = upload_to_feishu_drive(
        access_token=access_token,
        file_path=file_path,
        file_name=file_name,
        folder_token=config["folder_token"],
        config=config,
    )

    file_token = upload_result.get("file_token", "")
    doc_url = upload_result.get("url", "")

    if not file_token:
        print("\n⚠️  飞书上传失败，但本地报告已生成")
        print(f"   📁 本地文件：{file_path}")
        print("   请检查飞书应用配置（FEISHU_APP_ID / FEISHU_APP_SECRET）")
        return

    print("   ✅ 文件上传成功")

    # ── 第5步：输出结果 ──
    print("   3/3 完成")
    print()
    print("=" * 55)
    print("✅ 报告生成 & 飞书上传完成！")
    print("=" * 55)
    print(f"   📁 本地文件：{file_path}")
    print(f"   🔑 file_token：{file_token}")
    print(f"   🔗 飞书链接：{doc_url}")
    if config["folder_token"]:
        print(f"   📂 目标文件夹：{config['folder_token']}")
    print("=" * 55)

    # JSON 输出（供程序对接）
    print("\n📋 JSON 输出：")
    output = {
        "status": "success",
        "local_path": file_path,
        "file_token": file_token,
        "document_url": doc_url,
        "folder_token": config["folder_token"] or "root",
        "timestamp": datetime.now().isoformat(),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
