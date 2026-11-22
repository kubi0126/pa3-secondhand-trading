"""统计手写源代码行数，用于实验报告“源代码规模”一节。

口径：
- 代码行：非空且不以 # 开头的行（Python 文档字符串计入，属于源码）；
- 不统计测试、模板、CSS、构建产物；
- 单独列出模板与样式规模，便于说明 UI 工作量，但不计入 1500 行门槛。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "secondhand"
TEMPLATES = PACKAGE / "templates"
STATIC = PACKAGE / "static"


def python_stats(path: Path) -> tuple[int, int]:
    physical = 0
    code = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        physical += 1
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            code += 1
    return physical, code


def walk_files(root: Path, suffix: str) -> list[Path]:
    return sorted(
        path
        for path in root.rglob(f"*{suffix}")
        if "__pycache__" not in path.parts
    )


def collect() -> dict:
    modules: dict[str, dict[str, int]] = {}
    total_physical = 0
    total_code = 0
    for path in walk_files(PACKAGE, ".py"):
        if path.name == "__init__.py":
            group = path.parent.name or "secondhand"
        else:
            group = path.parent.name or "secondhand"
        physical, code = python_stats(path)
        bucket = modules.setdefault(group, {"files": 0, "physical": 0, "code": 0})
        bucket["files"] += 1
        bucket["physical"] += physical
        bucket["code"] += code
        total_physical += physical
        total_code += code

    templates = walk_files(TEMPLATES, ".html")
    template_lines = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in templates)
    styles = walk_files(STATIC, ".css")
    style_lines = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in styles)
    scripts = walk_files(STATIC, ".js")
    script_lines = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in scripts)

    return {
        "modules": modules,
        "summary": {
            "python_files": sum(item["files"] for item in modules.values()),
            "python_physical": total_physical,
            "python_code": total_code,
            "templates": len(templates),
            "template_lines": template_lines,
            "css_lines": style_lines,
            "js_lines": script_lines,
        },
    }


def render_markdown(data: dict) -> str:
    lines = [
        "# 源代码规模统计",
        "",
        "统计命令：`python tools/count_loc.py`",
        "",
        "| 包 | 文件数 | 物理行 | 代码行（非空非注释） |",
        "|---|---:|---:|---:|",
    ]
    for name, item in sorted(data["modules"].items()):
        lines.append(
            f"| {name} | {item['files']} | {item['physical']} | {item['code']} |"
        )
    summary = data["summary"]
    lines.extend(
        [
            f"| **合计** | **{summary['python_files']}** | "
            f"**{summary['python_physical']}** | **{summary['python_code']}** |",
            "",
            "## UI 资源（不计入 1500 行门槛）",
            "",
            f"- Jinja 模板：{summary['templates']} 个，{summary['template_lines']} 行",
            f"- CSS：{summary['css_lines']} 行",
            f"- JavaScript：{summary['js_lines']} 行",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--write", type=str, default="", help="写入 Markdown 文件")
    args = parser.parse_args()
    data = collect()
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    markdown = render_markdown(data)
    print(markdown)
    if args.write:
        Path(args.write).write_text(markdown, encoding="utf-8")
        print(f"\n已写入 {args.write}")


if __name__ == "__main__":
    main()
