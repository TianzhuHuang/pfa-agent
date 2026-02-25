#!/usr/bin/env python3
"""
PFA 持仓 JSON 校验工具

用法:
  python scripts/validate_portfolio.py                    # 从 stdin 读取 JSON
  python scripts/validate_portfolio.py portfolio.json    # 从文件读取

校验规则见 config/user-profile.schema.json。
"""

import json
import sys
from pathlib import Path
from typing import List, Tuple

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "config" / "user-profile.schema.json"


def load_schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_with_jsonschema(data: dict, schema: dict) -> Tuple[bool, List[str]]:
    try:
        import jsonschema
        jsonschema.validate(instance=data, schema=schema)
        return True, []
    except ImportError:
        # 无 jsonschema 时做最小校验
        return _minimal_validate(data, schema)
    except jsonschema.ValidationError as e:
        return False, [str(e)]


def _minimal_validate(data: dict, schema: dict) -> Tuple[bool, List[str]]:
    """无 jsonschema 时的最小校验：仅校验 holdings 中每项必填字段与 source 枚举。"""
    errs = []
    if "version" not in data:
        errs.append("缺少顶层字段: version")
    if "holdings" in data:
        if not isinstance(data["holdings"], list):
            errs.append("holdings 必须为数组")
        else:
            allowed_sources = {"ocr", "manual", "browser", "excel"}
            for i, item in enumerate(data["holdings"]):
                if not isinstance(item, dict):
                    errs.append(f"holdings[{i}] 必须为对象")
                    continue
                for key in ("symbol", "market", "source"):
                    if key not in item:
                        errs.append(f"holdings[{i}] 缺少必填字段: {key}")
                if item.get("source") and item["source"] not in allowed_sources:
                    errs.append(f"holdings[{i}].source 必须为: {list(allowed_sources)}")
                if item.get("market") and item["market"] not in ("A", "US", "HK", "OTHER"):
                    errs.append(f"holdings[{i}].market 必须为: A | US | HK | OTHER")
    return len(errs) == 0, errs


def main():
    schema = load_schema()
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if not path.exists():
            print(f"文件不存在: {path}", file=sys.stderr)
            sys.exit(2)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        try:
            data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(f"JSON 解析失败: {e}", file=sys.stderr)
            sys.exit(2)

    ok, errors = validate_with_jsonschema(data, schema)
    if ok:
        print("校验通过：持仓 JSON 符合 config/user-profile.schema.json")
        if data.get("holdings"):
            print(f"  共 {len(data['holdings'])} 条持仓。")
        sys.exit(0)
    else:
        print("校验未通过：", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
