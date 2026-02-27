#!/usr/bin/env python3
"""
PFA 本地环境初始化脚本

用途：解决「云端 Cursor 浏览器测试通过、本地 checkout 后打开网页报错」的环境差异。
请在项目根目录执行：python3 scripts/init_pfa_env.py

说明（为什么云端对、本地错）：
  - 云端：固定从仓库根目录启动、依赖已装、环境变量可能已配置。
  - 本地：可能未在根目录运行、缺依赖、缺 config 或 data 目录、未设 API Key。
本脚本会：安装依赖、创建缺失目录与占位配置、可选安装 Playwright 浏览器驱动。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# 项目根目录（脚本在 scripts/ 下）
ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str] | str, desc: str, optional: bool = False) -> bool:
    print(f"正在执行: {desc}...")
    try:
        if isinstance(cmd, str):
            subprocess.run(cmd, shell=True, check=True, cwd=str(ROOT))
        else:
            subprocess.run(cmd, check=True, cwd=str(ROOT))
        print(f"  ✅ {desc} 成功\n")
        return True
    except subprocess.CalledProcessError as e:
        if optional:
            print(f"  ⚠️ {desc} 跳过（可选步骤）\n")
            return False
        print(f"  ❌ {desc} 失败: {e}\n")
        return False


def main() -> None:
    print("=== PFA 本地环境初始化 ===\n")
    print(f"项目根目录: {ROOT}\n")

    # 1. 依赖
    req = ROOT / "requirements.txt"
    if not req.exists():
        print("  ⚠️ 未找到 requirements.txt，跳过 pip 安装。\n")
    else:
        run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
            "安装 requirements.txt 依赖",
        )
    # 面板常用（若未在 requirements 中）
    run(
        [sys.executable, "-m", "pip", "install", "pandas", "-q"],
        "确保 pandas 已安装（投研面板表格）",
        optional=True,
    )

    # 2. 目录结构（与 AGENTS.md / 代码中的路径一致）
    for d in ["data/raw", "data/store", "config"]:
        path = ROOT / d
        path.mkdir(parents=True, exist_ok=True)
        print(f"  📁 已确保目录: {d}")
    gitkeep = ROOT / "data" / "raw" / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("")
        print("  📁 已创建 data/raw/.gitkeep")
    print()

    # 3. 占位配置（仅当不存在时创建，不覆盖已有）
    portfolio_path = ROOT / "config" / "my-portfolio.json"
    if not portfolio_path.exists():
        portfolio_path.write_text(
            '{"version":"1.0","holdings":[],"channels":{"rss_urls":[],"xueqiu_user_ids":[],"twitter_handles":[]},"preferences":{}}',
            encoding="utf-8",
        )
        print("  📝 已创建 config/my-portfolio.json（空持仓）")
    sources_path = ROOT / "config" / "data-sources.json"
    if not sources_path.exists():
        sources_path.write_text(
            '{"rss_urls":[],"twitter_handles":[],"monitor_urls":[],"xueqiu_user_ids":[]}',
            encoding="utf-8",
        )
        print("  📝 已创建 config/data-sources.json")
    print()

    # 4. Playwright 浏览器驱动（仅在做本地浏览器 E2E 测试时需要）
    run(
        [sys.executable, "-m", "playwright", "install", "chromium", "--with-deps"],
        "安装 Playwright Chromium 驱动（可选，用于浏览器自动化测试）",
        optional=True,
    )

    # 5. 启动说明
    print("--- 本地启动控制中心 ---")
    print("  请在终端从项目根目录执行：")
    print("    cd " + str(ROOT))
    print("    streamlit run app/pfa_dashboard.py --server.port 8501")
    print()
    print("  浏览器打开: http://localhost:8501")
    print()
    print("  若需深度分析/审核：请设置环境变量 DASHSCOPE_API_KEY（及可选 OPENAI_API_KEY）。")
    print("  详见 AGENTS.md 与 docs/data-sources.md。")
    print("\n🚀 初始化完成。")


if __name__ == "__main__":
    main()
