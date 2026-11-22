"""打包实验三提交目录与 zip。

用法：
    python tools/package.py            # 要求 实验报告.pdf 已生成
    python tools/package.py --preview  # 用模板 PDF 生成预览 zip，便于检查结构
"""

from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STUDENT = "241220163_尹照达"
TARGET = ROOT / f"实验3_{STUDENT}"
REPORT = ROOT / "实验报告.pdf"
TEMPLATE = ROOT / "report" / "实验报告_模板.pdf"
UML = ROOT / "UML"
CODE = ROOT / "code"

IGNORE = shutil.ignore_patterns(
    "__pycache__", "*.pyc", ".pytest_cache", ".coverage", "coverage.xml",
    "htmlcov", "var", "*.db", "*.db-wal", "*.db-shm", "build", "dist",
    "*.egg-info", ".venv", "venv",
)


def prepare(preview: bool) -> Path:
    if REPORT.exists() and REPORT.stat().st_size > 50_000:
        report = REPORT
        zip_name = f"实验3_{STUDENT}.zip"
    elif preview and TEMPLATE.exists():
        report = TEMPLATE
        zip_name = f"实验3_{STUDENT}_预览.zip"
        print("警告：未找到 实验报告.pdf，使用模板生成预览 zip。")
    else:
        raise SystemExit(
            "未找到 实验报告.pdf。请先填写 report/report.html 并生成 "
            "pa3/实验报告.pdf，或使用 --preview 生成预览包。"
        )

    if TARGET.exists():
        shutil.rmtree(TARGET)
    TARGET.mkdir(parents=True)

    shutil.copy2(report, TARGET / "实验报告.pdf")
    shutil.copytree(UML, TARGET / "UML")
    shutil.copytree(CODE, TARGET / "code", ignore=IGNORE)

    zip_path = ROOT / zip_name
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(TARGET.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(ROOT))
    return zip_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true", help="允许用模板 PDF 生成预览包")
    args = parser.parse_args()
    zip_path = prepare(args.preview)
    count = sum(1 for _ in zipfile.ZipFile(zip_path).namelist())
    print(f"已生成 {zip_path}")
    print(f"包含 {count} 个文件，大小 {zip_path.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"解压后目录：{TARGET}")


if __name__ == "__main__":
    main()
