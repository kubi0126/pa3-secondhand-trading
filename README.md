# 实验三 软件实现与构建

校园二手交易系统的可运行原型，依据实验一需求与实验二 UML/数据设计实现。

## 目录

```
pa3/
├── code/          # 源码、测试、工具、README
├── UML/           # 实验二 13 对 UML（png + puml），实验三复用
├── docs/          # 代码规模、测试报告、设计映射、AI 使用记录、运行截图
├── report/        # 报告 HTML 模板、写作提纲、模板 PDF
├── 实验报告.pdf    # 待本人填写正文后生成（当前为模板）
└── 实验3_241220163_尹照达/  # 提交包（生成后）
```

## 当前状态

- 代码：8 个模块、75 个测试全部通过、覆盖率 81%、pylint 10.00/10。
- 规模：Python 手写代码 3503 行（非空非注释），超过 1500 行要求。
- UML：13 对 png/puml，已从实验二复制。
- 文档：`docs/` 下四份事实材料 + 17 页截图。
- 报告：`report/report.html` 为骨架，正文需本人按课程要求撰写。

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

课程明确“实验报告的书写不允许使用大模型的辅助”。`report/report.html` 只提供章节、
图表、命令与测试数据，黄色提示框需由本人替换为正文。填写后按
`report/report_outline.md` 文末命令重新生成 PDF。

## 提交

报告完成后生成：

```
实验3_241220163_尹照达/
├── 实验报告.pdf
├── UML/            # 13 对 png + puml
└── code/           # 源码（不含 var/、__pycache__、测试缓存）
```

详见 `report/report_outline.md` 的提交前检查清单。
