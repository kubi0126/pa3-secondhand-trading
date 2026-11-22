# 实验二 UML / UI 到实验三代码的映射

日期：2026-11-22　对应实现：`code/secondhand`

## 1. 用例图 → 路由

| 实验二用例 | 代码位置 | 说明 |
|---|---|---|
| U01 注册、U02 登录 | `web/routes_auth.py`、`services/auth_service.py` | 会话登录、失败锁定 |
| U03 保存草稿、U04 编辑商品、U05 提交审核、U06 下架 | `web/routes_items.py`、`services/item_service.py` | 商品生命周期 |
| U07 查看我的商品 | `web/routes_seller.py`、`templates/seller/items.html` | 卖家数据范围 |
| U08/U09 审核通过/驳回 | `web/routes_admin.py`、`services/audit_service.py` | 审核记录 + 日志 |
| U10 违规下架 | `services/audit_service.py::violation_delist` | 联动取消预约 |
| U11/U12 查询与详情 | `services/query_service.py`、`web/routes_items.py` | 多条件、分页、可见性 |
| U13 创建预约 | `services/reservation_service.py::create` | 先到先得、幂等 |
| U14 取消预约 | `reservation_service.py::cancel` | 释放商品 |
| U15 我的预约 | `web/routes_buyer.py` | 买家数据范围 |
| U16/U17/U18 确认/拒绝/完成 | `reservation_service.py`、`web/routes_seller.py` | 24h/48h 规则 |
| U19 待处理预约 | `web/routes_seller.py` | 只显示本人商品 |
| U20 操作日志 | `services/log_service.py`、`templates/logs.html` | 管理员全量、卖家本人 |
| U21/U22 统计 | `services/stat_service.py` | 分类统计、卖家统计 |
| U23 数据字典 | `services/dict_service.py`、`templates/admin/dict.html` | 分类/成色启停 |
| U24 自动过期 | `services/reservation_service.py::expire_due`、`scheduler.py`、`cli.py` | 线程或 CLI 触发 |

## 2. 类图 → 领域模型与仓储

| 类图中的类 | 代码 |
|---|---|
| User / Category / ItemCondition | `domain/models.py`、`repositories/user_repo.py`、`repositories/dict_repo.py` |
| Item | `domain/models.py::Item`、`repositories/item_repo.py` |
| Reservation | `domain/models.py::Reservation`、`repositories/reservation_repo.py` |
| AuditRecord | `domain/models.py::AuditRecord`、`repositories/audit_repo.py` |
| OperationLog | `domain/models.py::OperationLog`、`repositories/log_repo.py` |
| RequestLog | `domain/models.py::RequestLog`、`repositories/request_repo.py` |
| ItemStateMachine / ReservationStateMachine | `domain/state_machines.py` |
| AuthService / ItemService / AuditService / QueryService / ReservationService / LogService / StatService / SchedulerService | `services/` 下同名文件；字典服务对应 `DictService` |
| Repository 接口 | `repositories/` 下 7 个仓储类 |

类图中的关键方法映射：

- `Item.submitForReview/approve/reject/reserve/release/sell/delist/violationDelist`
  → `ItemService.submit`、`AuditService.approve/reject/violation_delist`、
  `ReservationService.create/complete`、`ItemService.delist`。
- `Reservation.confirm/cancel/reject/expire/complete`
  → `ReservationService` 同名方法。
- `User.canLogin` → `AuthService.login` 中的锁定与密码校验。

## 3. 状态图 → 代码

| 实验二状态图 | 代码 |
|---|---|
| 商品 8 状态、允许/禁止转换 | `domain/state_machines.py::ITEM_TRANSITIONS` |
| 预约 6 状态、允许/禁止转换 | `domain/state_machines.py::RESERVATION_TRANSITIONS` |
| 版本冲突返回 409 | 仓储 `change_status/update_content` 的 `WHERE version = ?`，服务层抛 `StateConflict` |
| 违规下架联动取消预约 | `AuditService.violation_delist` 同一事务内完成 |

## 4. 时序图 → 代码

### 4.1 创建预约（幂等校验 + 事务写入）

`ReservationService.create`：

1. 开启 `BEGIN IMMEDIATE`；
2. `RequestRepository.find/try_start` 占位；
3. 校验商品状态、卖家不能预约自己的商品、版本号；
4. 查询 60 秒内同买家同商品预约；
5. `INSERT reservation`；
6. `UPDATE item SET status='RESERVED' WHERE status='PUBLISHED' AND version=?`；
7. 写 `operation_log`；
8. `request_log` 标记 SUCCESS；
9. 提交。

对应 `tests/test_reservations.py::test_idempotent_request_returns_same_reservation`、
`tests/test_concurrency.py`。

### 4.2 违规下架（权限校验 + 事务联动）

`AuditService.violation_delist`：

1. 校验管理员与商品状态；
2. 查询有效预约；
3. 预约置为 CANCELLED，原因“商品被下架”；
4. 商品置为 VIOLATION_DELISTED；
5. 写两条日志；
6. 任一步失败回滚。

对应 `tests/test_reservations.py::test_violation_delist_cancels_active_reservation`。

## 5. 组件图 / 部署图 → 代码结构

| 实验二组件 | 代码 |
|---|---|
| 浏览器（PC/手机） | `templates/` + `static/css/app.css`，响应式布局 |
| REST 接口层 | `web/routes_*.py`（Flask 路由） |
| 应用服务 | `services/*.py` |
| 领域状态机 | `domain/state_machines.py` |
| 数据访问层 | `repositories/*.py` |
| MySQL | `schema.sql` + SQLite（实现替代） |
| 定时任务 | `scheduler.py` + `flask expire` |

部署差异：实验二为 Nginx → JVM → MySQL 单机；本实现为 Flask 开发服务器 → SQLite 单文件。
差异原因与替换方案见 `code/README.md` 第 6 节。

## 6. UI 15 屏 → 模板

| 实验二界面 | 模板 | 路由 |
|---|---|---|
| D01 登录/注册 | `auth/login.html`、`auth/register.html` | `/login`、`/register` |
| D02 商品列表 | `items/list.html` | `/` |
| D03 商品详情/预约 | `items/detail.html` | `/items/<id>` |
| D04 发布/编辑商品 | `items/form.html` | `/items/new`、`/items/<id>/edit` |
| D05 我的商品 | `seller/items.html` | `/my/items` |
| D06 我的预约 | `buyer/reservations.html` | `/my/reservations` |
| D07 待处理预约 | `seller/reservations.html` | `/seller/reservations` |
| D08 审核工作台 | `admin/review.html` | `/admin/review` |
| D09 违规下架 | `admin/items.html` | `/admin/items` |
| D10 操作日志 | `logs.html` | `/admin/logs` |
| D11 统计面板 | `admin/stats.html` | `/admin/stats` |
| D12 数据字典 | `admin/dict.html` | `/admin/dict` |
| D13 卖家商品日志 | `logs.html`（scope=seller） | `/seller/logs` |
| M01/M02 移动端 | 同一模板的响应式布局 | 同 D02/D03 |

窄屏适配在 `app.css` 的 `@media (max-width: 820px)` 中完成：导航横向滚动、单列卡片、
表格横向滚动、弹层改为文档流。
