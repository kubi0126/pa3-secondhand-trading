# 运行截图清单

截图目录：`docs/screenshots/`
截取环境：Chrome（Playwright，桌面 1440×900，移动 390×844）
演示数据：`python -m secondhand` 首次启动自动写入

| 文件 | 页面/路由 | 说明 |
|---|---|---|
| 01-商品列表.png | `/` | 买家/访客浏览、筛选、排序、分页 |
| 02-商品详情.png | `/items/2` | 未登录详情与“登录后预约” |
| 03-登录.png | `/login` | 登录表单与演示账号 |
| 04-我的预约.png | `/my/reservations` | 买家预约列表、状态标签、取消入口 |
| 05-买家详情-预约入口.png | `/items/2` | 登录买家可发起预约 |
| 06-我的商品.png | `/my/items` | 卖家统计卡、状态 Tab、行内操作 |
| 07-发布商品.png | `/items/new` | 发布表单、必填与提示 |
| 08-待处理预约.png | `/seller/reservations` | 待确认、剩余时间、确认/拒绝 |
| 09-已确认预约-完成入口.png | `/seller/reservations?status=CONFIRMED` | 标记交易完成 |
| 10-卖家商品日志.png | `/seller/logs` | 卖家仅见自己商品相关日志 |
| 11-审核工作台.png | `/admin/review` | 审核通过/驳回（原因必填） |
| 12-商品处置.png | `/admin/items` | 违规下架入口 |
| 13-操作日志.png | `/admin/logs` | 全量日志、筛选 |
| 14-统计面板.png | `/admin/stats` | 分类统计与口径说明 |
| 15-数据字典.png | `/admin/dict` | 分类/成色启停与新增 |
| 16-移动端-商品列表.png | `/` | 390×844 窄屏 |
| 17-移动端-商品详情.png | `/items/2` | 390×844 窄屏 |
| 18-GitHub仓库首页.png | GitHub | Public、main、文件列表 |
| 19-GitHub提交记录.png | GitHub | 4 次主要提交 |

复现截图需先启动服务：

```bash
cd code
python -m secondhand
# 另开终端
pip install playwright
python ../tools/shoot_screenshots.py
```

脚本会依次登录 alice/bob/admin 并截取 19 张图；需要本机安装 Chrome。
