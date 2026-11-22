# 测试与代码质量报告

日期：2026-11-22
被测版本：`code/`（Git 提交见仓库）

## 1. 环境

| 项 | 版本 |
|---|---|
| 操作系统 | Windows 11 |
| Python | 3.13.14 |
| Flask | 3.1.3 |
| pytest | 9.2.0 |
| bcrypt | 4.x（cost=12；测试环境 cost=4） |
| SQLite | 3.45+（WAL 模式） |

## 2. 执行命令与结果

```bash
cd code
python -m pytest -q
# 75 passed in 8.58s

python -m pytest --cov=secondhand --cov-report=term-missing
# TOTAL 2132 statements, 396 missed, 81%

python -m pylint secondhand
# Your code has been rated at 10.00/10

python tools/count_loc.py
# Python 3500 行（非空非注释，41 个文件）
# Jinja 1044 行、CSS 496 行（不计入 1500 行门槛）
```

## 3. 测试分布

| 文件 | 用例数（含参数化） | 覆盖内容 |
|---|---:|---|
| `test_state_machines.py` | 29 | 商品 11 条允许/7 条禁止、预约 7 条允许/4 条禁止转换 |
| `test_auth.py` | 12 | 注册、重复用户名/手机号、格式校验、bcrypt、5 次锁定、成功重置 |
| `test_items.py` | 9 | 草稿→提交→审核、改价重审、只改描述、旧版本冲突、下架限制、可见性、非法价格/URL |
| `test_reservations.py` | 9 | 创建锁定、幂等、取消/拒绝释放、确认+完成、权限、超时过期、违规联动 |
| `test_concurrency.py` | 2 | 两买家并发预约仅 1 条成功；同 request_id 并发仅 1 条记录 |
| `test_web.py` | 14 | 页面渲染、角色拦截、CSRF、表单创建、草稿越权、404 |
| **合计** | **75** | |

## 4. 重点场景与断言

1. **并发先到先得**：两个线程同时预约同一商品，结果恰好 1 个成功、1 个 `StateConflict`；
   数据库中该商品的有效预约数为 1，商品状态为 `RESERVED`。
2. **幂等**：同一 `request_id` 连续提交返回同一预约 ID，不新建记录；
   同一 `request_id` 并发提交只落 1 条预约。
3. **违规下架联动**：管理员下架已预约商品后，商品为 `VIOLATION_DELISTED`，
   预约自动变为 `CANCELLED`，取消原因为“商品被下架”。
4. **超时过期**：把 `expire_at` 改为过去时间后调用 `expire_due()`，
   预约变为 `EXPIRED`，商品恢复 `PUBLISHED`，日志操作人为 `SYSTEM`。
5. **旧版本冲突**：同一商品连续两次修改，第二次携带旧 `version` 返回 `StateConflict`。
6. **权限**：非卖家不能操作预约；非管理员访问 `/admin/*` 被重定向；草稿详情对他人返回 403。
7. **CSRF**：开启 CSRF 后，无 token 的 POST 返回 400；正常表单携带 token 通过。

## 5. 覆盖率说明

- 总覆盖率 81%。未覆盖部分主要是：`__main__`/`scheduler` 的进程入口、
  CLI 命令、管理员字典的增删启停、部分路由的异常分支。
- 核心业务（状态机、预约、审核、商品、账号）覆盖率均在 79%–100%。
- 前端模板与 CSS 不计入 Python 覆盖率。

## 6. 代码风格

- `pylint` 10.00/10。项目 `.pylintrc` 关闭了与原型规模相关的设计复杂度告警
  （实体属性多、服务参数多、类无公共方法等），保留错误、未使用变量、未定义变量、
  异常处理与安全问题检查。
- 手工修复的告警：`db.py` 内部函数遮蔽外层 `get_db`、`scheduler.py` 的宽泛异常捕获、
  未使用导入、行宽超限。
- 命名与分层：路由只做参数解析与跳转，业务规则在 `services/`，SQL 在 `repositories/`，
  状态规则在 `domain/state_machines.py`。

## 7. 未覆盖/待补

- 10 万商品、50 并发的压测未执行；当前只验证了并发正确性，未验证 P95 指标。
- 日志 1 年保留的归档任务未实现；`request_log` 提供 7 天清理命令。
- 浏览器兼容性只验证 Chrome/Edge 当前版本与 390px 窄屏布局。
- 报告正文按课程要求由本人撰写，不在本测试报告范围内。
