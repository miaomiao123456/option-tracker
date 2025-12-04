"""
智能Cookies保存工具 - 自动检测登录状态并保存cookies
使用方法: python3 save_cookies_smart.py
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# cookies保存目录
COOKIES_DIR = Path(__file__).parent / ".cookies"
COOKIES_DIR.mkdir(exist_ok=True)

# 配置
SITES = [
    {
        "name": "智汇期讯",
        "url": "https://hzzhqx.com/home",
        "cookies_file": "zhihui_cookies.json",
        "login_check_selectors": [
            "text=退出",
            "text=登出",
            "text=个人中心",
            "[class*='user']",
            "[class*='logout']"
        ],
        "login_url_patterns": ["login", "signin"]
    },
    {
        "name": "融达数据",
        "url": "https://dt.rongdaqh.com/finance_and_economics/calendar",
        "cookies_file": "rongda_cookies.json",
        "login_check_selectors": [
            "text=退出",
            "text=登出",
            "text=个人中心",
            "[class*='user']",
            "[class*='logout']"
        ],
        "login_url_patterns": ["login", "signin"]
    }
]


async def check_if_logged_in(page, site_config):
    """检查是否已登录"""
    # 方法1: 检查URL是否包含login关键词
    current_url = page.url.lower()
    for pattern in site_config["login_url_patterns"]:
        if pattern in current_url:
            return False

    # 方法2: 检查页面是否有登录后的元素
    for selector in site_config["login_check_selectors"]:
        try:
            element = await page.query_selector(selector)
            if element:
                logger.info(f"✅ 检测到登录元素: {selector}")
                return True
        except:
            pass

    # 方法3: 检查cookies数量
    cookies = await page.context.cookies()
    if len(cookies) > 5:  # 登录后通常会有多个cookies
        logger.info(f"✅ 检测到 {len(cookies)} 个cookies，可能已登录")
        return True

    return False


async def save_site_cookies(site_config):
    """保存单个网站的cookies"""

    print(f"\n{'=' * 70}")
    print(f"🌐 {site_config['name']}")
    print(f"{'=' * 70}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        try:
            logger.info(f"正在打开 {site_config['name']} ...")
            await page.goto(site_config["url"], wait_until="domcontentloaded", timeout=60000)

            print(f"\n📋 操作说明：")
            print(f"   1. 浏览器窗口已打开，请在窗口中完成登录")
            print(f"   2. 账号: 18321399574")
            print(f"   3. 密码: yi2013405")
            print(f"   4. 登录完成后，程序会自动检测并保存cookies")
            print(f"   5. 最多等待 5 分钟")
            print(f"\n⏱️  检测中", end="", flush=True)

            # 每5秒检查一次，最多检查60次 (5分钟)
            max_checks = 60
            check_interval = 5

            for i in range(max_checks):
                await asyncio.sleep(check_interval)
                print(".", end="", flush=True)

                # 检查是否已登录
                if await check_if_logged_in(page, site_config):
                    print("\n")
                    logger.info(f"✅ 检测到登录成功！")

                    # 等待2秒确保所有cookies都已设置
                    await asyncio.sleep(2)

                    # 保存cookies
                    cookies = await context.cookies()
                    cookies_file = COOKIES_DIR / site_config["cookies_file"]

                    with open(cookies_file, 'w', encoding='utf-8') as f:
                        json.dump(cookies, f, ensure_ascii=False, indent=2)

                    logger.info(f"✅ Cookies已保存: {cookies_file}")
                    logger.info(f"   共保存 {len(cookies)} 个cookies")

                    print(f"\n{'=' * 70}")
                    print(f"✅ {site_config['name']} - Cookies保存成功！")
                    print(f"{'=' * 70}\n")

                    await asyncio.sleep(2)  # 稍等再关闭浏览器
                    break

                # 每30秒显示剩余时间
                if (i + 1) % 6 == 0:
                    remaining = max_checks - i - 1
                    remaining_seconds = remaining * check_interval
                    print(f" ({remaining_seconds}秒)", end="", flush=True)

            else:
                # 超时未检测到登录
                print("\n")
                logger.warning(f"⚠️ 5分钟内未检测到登录，尝试保存当前cookies...")

                cookies = await context.cookies()
                if len(cookies) > 0:
                    cookies_file = COOKIES_DIR / site_config["cookies_file"]
                    with open(cookies_file, 'w', encoding='utf-8') as f:
                        json.dump(cookies, f, ensure_ascii=False, indent=2)
                    logger.info(f"已保存 {len(cookies)} 个cookies（可能未完全登录）")
                else:
                    logger.error(f"❌ 未获取到任何cookies")

        except Exception as e:
            logger.error(f"保存 {site_config['name']} cookies失败: {e}")

        finally:
            await browser.close()


async def main():
    """主函数"""

    print("\n" + "=" * 70)
    print("🍪 智能Cookies保存工具")
    print("=" * 70)
    print("\n本工具会自动检测登录状态并保存cookies")
    print("将依次打开两个网站，请在浏览器中完成登录")
    print("=" * 70)

    for site_config in SITES:
        await save_site_cookies(site_config)
        await asyncio.sleep(2)  # 两个网站之间间隔2秒

    print("\n" + "=" * 70)
    print("🎉 所有Cookies保存完成！")
    print("=" * 70)
    print("\n现在可以运行爬虫测试:")
    print("  python3 test_fixed_crawlers.py")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
