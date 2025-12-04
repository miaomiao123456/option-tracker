"""
手动登录并保存cookies的脚本
使用方法: python3 save_cookies.py
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


async def save_zhihui_cookies():
    """手动登录智汇期讯并保存cookies"""
    logger.info("=" * 60)
    logger.info("智汇期讯 - 手动登录保存cookies")
    logger.info("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        try:
            # 打开登录页面
            await page.goto("https://hzzhqx.com/home", wait_until="domcontentloaded")

            logger.info("\n⏰ 请在打开的浏览器中手动完成登录")
            logger.info("登录成功后，在控制台输入 'y' 并回车保存cookies\n")

            # 等待用户确认登录完成
            user_input = input("登录完成了吗? (输入 y 保存cookies): ")

            if user_input.lower() == 'y':
                # 保存cookies
                cookies = await context.cookies()
                cookies_file = COOKIES_DIR / "zhihui_cookies.json"

                with open(cookies_file, 'w', encoding='utf-8') as f:
                    json.dump(cookies, f, ensure_ascii=False, indent=2)

                logger.info(f"✅ cookies已保存到: {cookies_file}")
                logger.info(f"   共保存 {len(cookies)} 个cookies")
            else:
                logger.info("❌ 取消保存cookies")

        except Exception as e:
            logger.error(f"保存失败: {e}")

        finally:
            await browser.close()


async def save_rongda_cookies():
    """手动登录融达数据并保存cookies"""
    logger.info("\n" + "=" * 60)
    logger.info("融达数据 - 手动登录保存cookies")
    logger.info("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        try:
            # 打开登录页面
            await page.goto("https://dt.rongdaqh.com/finance_and_economics/calendar",
                          wait_until="domcontentloaded")

            logger.info("\n⏰ 请在打开的浏览器中手动完成登录")
            logger.info("登录成功后，在控制台输入 'y' 并回车保存cookies\n")

            # 等待用户确认登录完成
            user_input = input("登录完成了吗? (输入 y 保存cookies): ")

            if user_input.lower() == 'y':
                # 保存cookies
                cookies = await context.cookies()
                cookies_file = COOKIES_DIR / "rongda_cookies.json"

                with open(cookies_file, 'w', encoding='utf-8') as f:
                    json.dump(cookies, f, ensure_ascii=False, indent=2)

                logger.info(f"✅ cookies已保存到: {cookies_file}")
                logger.info(f"   共保存 {len(cookies)} 个cookies")
            else:
                logger.info("❌ 取消保存cookies")

        except Exception as e:
            logger.error(f"保存失败: {e}")

        finally:
            await browser.close()


async def main():
    print("\n" + "=" * 60)
    print("🍪 Cookies保存工具")
    print("=" * 60)
    print("\n选择要保存cookies的网站:")
    print("1. 智汇期讯")
    print("2. 融达数据")
    print("3. 两个都保存")

    choice = input("\n请输入选项 (1/2/3): ")

    if choice == '1':
        await save_zhihui_cookies()
    elif choice == '2':
        await save_rongda_cookies()
    elif choice == '3':
        await save_zhihui_cookies()
        await asyncio.sleep(2)
        await save_rongda_cookies()
    else:
        print("无效选项")


if __name__ == "__main__":
    asyncio.run(main())
