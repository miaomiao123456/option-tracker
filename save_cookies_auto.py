"""
自动保存智汇期讯和融达数据的cookies（非交互式版本）
使用方法: python3 save_cookies_auto.py
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


async def save_both_cookies():
    """自动打开两个网站供手动登录并保存cookies"""

    print("\n" + "=" * 70)
    print("🍪 自动Cookies保存工具")
    print("=" * 70)
    print("\n即将依次打开两个网站的浏览器窗口")
    print("请在每个浏览器窗口中完成登录")
    print("=" * 70)

    # 1. 智汇期讯
    print("\n【1/2】智汇期讯")
    print("-" * 70)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        try:
            logger.info("正在打开智汇期讯登录页面...")
            await page.goto("https://hzzhqx.com/home", wait_until="domcontentloaded")

            print("\n⏰ 浏览器已打开，请完成以下操作：")
            print("   1. 在浏览器中登录（账号: 18321399574, 密码: yi2013405）")
            print("   2. 登录成功后，等待60秒...")
            print("   3. 程序会自动保存cookies并关闭浏览器")
            print("-" * 70)

            # 等待60秒供用户登录
            await asyncio.sleep(60)

            # 保存cookies
            cookies = await context.cookies()
            cookies_file = COOKIES_DIR / "zhihui_cookies.json"

            with open(cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ 智汇期讯cookies已保存: {cookies_file}")
            logger.info(f"   共保存 {len(cookies)} 个cookies")

        except Exception as e:
            logger.error(f"保存智汇期讯cookies失败: {e}")

        finally:
            await browser.close()

    # 等待3秒再打开下一个
    await asyncio.sleep(3)

    # 2. 融达数据
    print("\n【2/2】融达数据")
    print("-" * 70)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        try:
            logger.info("正在打开融达数据登录页面...")
            await page.goto("https://dt.rongdaqh.com/finance_and_economics/calendar",
                          wait_until="domcontentloaded")

            print("\n⏰ 浏览器已打开，请完成以下操作：")
            print("   1. 在浏览器中登录（账号: 18321399574, 密码: yi2013405）")
            print("   2. 登录成功后，等待60秒...")
            print("   3. 程序会自动保存cookies并关闭浏览器")
            print("-" * 70)

            # 等待60秒供用户登录
            await asyncio.sleep(60)

            # 保存cookies
            cookies = await context.cookies()
            cookies_file = COOKIES_DIR / "rongda_cookies.json"

            with open(cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ 融达数据cookies已保存: {cookies_file}")
            logger.info(f"   共保存 {len(cookies)} 个cookies")

        except Exception as e:
            logger.error(f"保存融达数据cookies失败: {e}")

        finally:
            await browser.close()

    print("\n" + "=" * 70)
    print("✅ 完成！所有cookies已保存")
    print("=" * 70)
    print("\n现在可以运行爬虫，它们会自动使用cookies登录")
    print("测试命令: python3 test_fixed_crawlers.py")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(save_both_cookies())
