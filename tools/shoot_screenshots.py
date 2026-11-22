from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
OUT = Path(r"C:/Users/尹照达/Desktop/作业/软件工程/pa3/docs/screenshots")
OUT.mkdir(parents=True, exist_ok=True)

def login(page, username, password):
    page.goto(f"{BASE}/login")
    page.fill('input[name="login"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")

def shot(page, name):
    page.wait_for_timeout(250)
    page.screenshot(path=str(OUT / name), full_page=True)
    print("saved", name, page.url)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
    page = ctx.new_page()

    page.goto(BASE + "/")
    shot(page, "01-商品列表.png")
    page.goto(BASE + "/items/2")
    shot(page, "02-商品详情.png")
    page.goto(BASE + "/login")
    shot(page, "03-登录.png")

    login(page, "bob", "User@123")
    page.goto(BASE + "/my/reservations")
    shot(page, "04-我的预约.png")
    page.goto(BASE + "/items/2")
    shot(page, "05-买家详情-预约入口.png")

    ctx2 = browser.new_context(viewport={"width": 1440, "height": 900})
    page2 = ctx2.new_page()
    login(page2, "alice", "User@123")
    page2.goto(BASE + "/my/items")
    shot(page2, "06-我的商品.png")
    page2.goto(BASE + "/items/new")
    shot(page2, "07-发布商品.png")
    page2.goto(BASE + "/seller/reservations")
    shot(page2, "08-待处理预约.png")
    # 确认第一条预约，便于截取“已确认”状态与完成入口
    confirm = page2.query_selector('form[action*="/confirm"] button')
    if confirm:
        confirm.click()
        page2.wait_for_load_state("networkidle")
    page2.goto(BASE + "/seller/reservations?status=CONFIRMED")
    shot(page2, "09-已确认预约-完成入口.png")
    page2.goto(BASE + "/seller/logs")
    shot(page2, "10-卖家商品日志.png")

    ctx3 = browser.new_context(viewport={"width": 1440, "height": 900})
    page3 = ctx3.new_page()
    login(page3, "admin", "Admin@123")
    page3.goto(BASE + "/admin/review")
    shot(page3, "11-审核工作台.png")
    page3.goto(BASE + "/admin/items")
    shot(page3, "12-商品处置.png")
    page3.goto(BASE + "/admin/logs")
    shot(page3, "13-操作日志.png")
    page3.goto(BASE + "/admin/stats")
    shot(page3, "14-统计面板.png")
    page3.goto(BASE + "/admin/dict")
    shot(page3, "15-数据字典.png")

    mobile = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    mp = mobile.new_page()
    mp.goto(BASE + "/")
    shot(mp, "16-移动端-商品列表.png")
    mp.goto(BASE + "/items/2")
    shot(mp, "17-移动端-商品详情.png")

    browser.close()
