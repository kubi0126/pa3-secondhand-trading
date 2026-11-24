# 实验三 软件实现与构建

校园二手交易系统的可运行原型，依据实验一需求与实验二 UML/数据设计实现。

## 目录

```
pa3/
├── code/          # 源码、测试、工具、README
├── UML/           # 实验二 13 对 UML（png + puml），实验三复用
├── docs/          # 代码规模、测试报告、设计映射、AI 使用记录、运行截图
├── report/        # 报告源、写作提纲与历史稿
├── 实验报告.pdf    # 最终报告（提交物）
└── 实验3_241220163_尹照达/  # 提交包（生成后）
```

## 当前状态

- 代码：8 个模块、75 个测试全部通过、覆盖率 81%、pylint 10.00/10。
- 规模：Python 手写代码 3503 行（非空非注释），超过 1500 行要求。
- UML：13 对 png/puml，已从实验二复制。
- 文档：`docs/` 下四份事实材料 + 19 张运行/Git 截图。
- 报告：最终 PDF 作为提交物；报告源仅存本地，不纳入 Git。
- 收尾排期（历史计划，已完成）：`docs/archive/implementation_plan_2026-11-22.md`。

## 快速开始

```bash
cd code
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m secondhand
# http://127.0.0.1:5000
```

演示账号：`admin / Admin@123`、`alice / User@123`、`bob / User@123`。

## 验证命令

```bash
cd code
python -m pytest -q
python -m pytest --cov=secondhand --cov-report=term-missing
python -m pylint secondhand tests
python tools/count_loc.py
```

## 报告

课程明确“实验报告的书写不允许使用大模型的辅助”。报告源仅存本地，不纳入 Git；提交物为 zip 中的 `实验报告.pdf`。仓库只保留代码、测试、UML 与文档。

## 提交

报告完成后生成：

```
实验3_241220163_尹照达/
├── 实验报告.pdf
├── UML/            # 13 对 png + puml
└── code/           # 源码（不含 var/、__pycache__、测试缓存）
```

详见 `report/report_outline.md` 的提交前检查清单。
