# 校园二手交易系统（实验三实现）

依据实验一的需求与实验二的 UML/数据设计实现的 B/S 原型。后端使用 Python 3 + Flask，
数据存储使用 SQLite，页面使用 Jinja 服务端渲染并复用实验二的视觉规范。

## 1. 与实验一、实验二的对应

| 实验二设计 | 本实现 |
|---|---|
| 8 个模块 M1–M8 | `services/` 下 9 个服务类，按模块拆分 |
| 8 个实体 + 4 个枚举 | `domain/models.py`、`domain/enums.py` |
| 商品/预约状态图 | `domain/state_machines.py`，允许/禁止转换逐条编码 |
| 类图、组件图 | `repositories/` + `services/` + `web/` 三层 |
| 部署图（Nginx → JVM → MySQL） | Flask 开发服务器 → SQLite（课程原型，差异见第 6 节） |
| 15 屏 UI | `templates/` 下 16 个模板，覆盖桌面与窄屏 |
| MySQL 8.0 DDL | `schema.sql`，CHECK + 部分唯一索引表达同等约束 |

## 2. 目录结构

```
code/
├── app.py                     # Flask 入口（flask --app app run）
├── secondhand/
│   ├── __main__.py            # python -m secondhand
│   ├── config.py              # 配置（分页、锁定、超时等）
│   ├── db.py                  # 连接、事务、Flask 生命周期
│   ├── schema.sql             # 8 张表、索引、唯一约束
│   ├── seed.py                # 字典、演示账号与示例商品
│   ├── scheduler.py           # 预约超时扫描线程
│   ├── cli.py                 # flask expire / cleanup-requests
│   ├── domain/                # 枚举、实体、异常、状态机
│   ├── repositories/          # 6 类仓储 + 字典仓储
│   ├── services/              # 账号、商品、审核、查询、预约、日志、统计、字典
│   ├── web/                   # 应用工厂、蓝图、CSRF、登录装饰器
│   ├── templates/             # Jinja 页面
│   └── static/css/app.css     # 设计系统
├── tests/                     # 137 个单元/集成/并发测试
├── tools/count_loc.py         # 源代码规模统计
├── requirements.txt
├── pyproject.toml
└── .pylintrc
```

## 3. 快速开始

```bash
cd code
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python -m secondhand            # 或 flask --app app run
```

浏览器访问 <http://127.0.0.1:5000>。首次启动会自动建库并写入演示数据，数据库文件在
`var/secondhand.db`；删除该文件即可重置。

### 演示账号

| 角色 | 账号 | 密码 |
|---|---|---|
| 管理员 | `admin` | `Admin@123` |
| 卖家/买家 | `alice` | `User@123` |
| 买家 | `bob` | `User@123` |
| 买家 | `carol` | `User@123` |

## 4. 功能范围

- **访客**：浏览已发布商品，按关键词、分类、价格区间查询，按价格/发布时间排序与分页；查看已发布/已预约商品详情。
- **普通用户（买卖同号）**：注册登录；保存草稿、编辑、提交审核、下架；创建/取消预约；查看我的预约与取消原因；处理自己商品的待确认预约（确认/拒绝）与已确认预约（标记完成）；查看个人统计与商品日志。
- **管理员**：审核通过/驳回（驳回原因必填）；违规下架并联动取消有效预约；商品处置列表；全量日志查询；分类统计；分类/成色字典维护。
- **系统任务**：24 小时未确认、48 小时未完成自动过期并释放商品；写系统类型日志。

本期不实现：在线支付、物流、站内聊天、图片上传、用户封禁、实名认证、举报客服。
商品不提供物理删除，已下架/违规下架为终态。

## 5. 关键实现

- **状态机**：商品 8 状态、预约 6 状态的允许转换集中在 `state_machines.py`，服务层在写库前校验。
- **唯一有效预约**：SQLite 部分唯一索引 `uk_active_item`、`uk_active_buyer_item` 兜底并发。
- **乐观锁**：商品与预约均带 `version`，更新语句 `WHERE version = ?`，影响行数为 0 返回 409。
- **幂等**：预约创建要求 `request_id`，`request_log` 原子占位；重复请求返回首次预约；60 秒内同买家同商品重复预约直接返回原记录。
- **事务**：关键写操作使用 `BEGIN IMMEDIATE`，业务数据、状态与操作日志同事务提交；违规下架“取消预约 + 下架 + 两条日志”整体回滚。
- **安全**：bcrypt 加盐哈希、登录失败 5 次锁定 15 分钟、角色装饰器、CSRF token、参数化 SQL、图片 URL 仅允许 http/https。
- **日志**：商品与预约的关键动作写入 `operation_log`；管理员查全量，卖家只能查自己商品相关日志。

## 6. 与实验二设计的差异

实验三允许实现与设计不一致。本实现的选择与理由：

1. **语言/框架**：实验二部署图写的是 JVM，本机没有 JDK；改用 Python + Flask，便于在课程周期内完成并保证可运行。
2. **数据库**：MySQL 8.0 → SQLite。表名、字段、CHECK、唯一约束尽量保持同名同义；MySQL 的生成列唯一索引改为 SQLite 部分唯一索引。SQLite 适合单机演示，后续可替换为 MySQL。
3. **接口形态**：组件图的 REST 接口层在本实现中表现为 Flask 资源路由 + 服务端渲染表单；服务层与仓储层仍保持分层，便于替换为 JSON API。
4. **部署**：Nginx + 独立应用进程 → Flask 开发服务器单进程；生产部署不在本实验范围。
5. **性能**：未做 10 万商品/50 并发压测；已按实验二的索引与分页上限实现，压测留待后续实验。

## 7. 测试与代码质量

```bash
python -m pytest -q                                # 137 passed
python -m pytest --cov=secondhand --cov-report=term-missing
python -m pylint secondhand                        # 10.00/10（项目 .pylintrc）
python tools/count_loc.py                          # 代码规模
```

当前统计：Python 手写代码 **3508 行**（非空非注释，41 个文件，不含测试/模板/CSS），
Jinja 模板 1045 行、CSS 496 行。详细数字见 `../docs/loc_report.md`。

## 8. 常用命令

```bash
flask --app app expire                    # 手动触发超时扫描
flask --app app cleanup-requests --days 7 # 清理幂等请求记录
python -m build                           # 构建 wheel（需 pip install build）
```

## 9. 已知限制

- SQLite 的并发能力弱于 MySQL，压测数据不能直接外推到生产。
- 日志保留 1 年目前是约定与索引设计，未实现归档任务；`request_log` 提供清理命令。
- 除预约创建外，其余写操作以“version + 状态机”保证重复提交只产生一次效果，第二次返回 409；
  未为每个写接口单独引入 `request_id`。
- 报告正文按课程要求由本人撰写，本目录只提供代码、测试、截图与事实材料。
