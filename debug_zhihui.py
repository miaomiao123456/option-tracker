"""调试智汇期讯登录"""
import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_zhihui():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--no-sandbox'])
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        try:
            logger.info("打开智汇期讯登录页面...")
            await page.goto("https://hzzhqx.com/home", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)

            logger.info(f"页面标题: {await page.title()}")

            # 查找所有input元素
            inputs = await page.query_selector_all("input")
            logger.info(f"页面共有 {len(inputs)} 个input元素")

            for i, inp in enumerate(inputs):
                placeholder = await inp.get_attribute("placeholder") or ""
                name = await inp.get_attribute("name") or ""
                type_attr = await inp.get_attribute("type") or ""
                logger.info(f"  Input {i}: type={type_attr}, name={name}, placeholder={placeholder}")

            # 查找登录相关按钮
            login_texts = ["登录", "登錄", "login", "Login"]
            for text in login_texts:
                elements = await page.query_selector_all(f"text={text}")
                if elements:
                    logger.info(f"找到包含'{text}'的元素: {len(elements)}个")

            # 截图保存
            screenshot_path = "/Users/pm/Documents/期权交易策略/option_tracker/debug_zhihui.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            logger.info(f"截图已保存: {screenshot_path}")

            # 保持浏览器打开60秒供查看
            logger.info("浏览器将保持打开60秒...")
            await asyncio.sleep(60)

        except Exception as e:
            logger.error(f"调试失败: {e}", exc_info=True)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_zhihui())
