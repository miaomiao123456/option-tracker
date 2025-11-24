"""
交易可查爬虫 - jiaoyikecha.com
功能：
1. 登录获取session
2. 爬取席位资金数据
3. 爬取每日交易蓝图图片
"""
import asyncio
import logging
from datetime import datetime, date
from typing import Optional, List, Dict
from playwright.async_api import async_playwright, Page, Browser
from config.settings import get_settings
from pathlib import Path
import json
import time

logger = logging.getLogger(__name__)
settings = get_settings()


class JiaoyiKechaSpider:
    """交易可查爬虫类"""

    def __init__(self):
        self.settings = settings
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.is_logged_in = False
        self.save_dir = Path(__file__).parent.parent.parent / "交易可查" / "images"
        self.save_dir.mkdir(parents=True, exist_ok=True)

    async def init_browser(self, headless: bool = True):
        """初始化浏览器"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=headless,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        self.page = await context.new_page()
        logger.info("浏览器初始化成功")

    async def login(self) -> bool:
        """登录交易可查"""
        try:
            logger.info("开始登录交易可查...")
            await self.page.goto("https://www.jiaoyikecha.com/", wait_until="networkidle")

            # 等待登录按钮出现并点击
            await self.page.wait_for_selector("text=登录", timeout=10000)
            await self.page.click("text=登录")
            await asyncio.sleep(2)

            # 输入账号密码
            await self.page.fill("input[placeholder*='手机号']", self.settings.JYK_USER)
            await self.page.fill("input[placeholder*='密码']", self.settings.JYK_PASS)

            # 点击登录按钮
            await self.page.click("button:has-text('登录')")

            # 等待登录成功 - 可能跳转到首页或个人中心
            try:
                await self.page.wait_for_url("**/user/home", timeout=15000)
                self.is_logged_in = True
                logger.info("登录成功!")
                return True
            except:
                # 检查是否已经在主页
                current_url = self.page.url
                if "user" in current_url or "home" in current_url:
                    self.is_logged_in = True
                    logger.info("登录成功!")
                    return True
                else:
                    logger.error(f"登录失败，当前URL: {current_url}")
                    return False

        except Exception as e:
            logger.error(f"登录过程出错: {e}")
            return False

    async def fetch_daily_blueprint(self, target_date: Optional[date] = None) -> Optional[Dict]:
        """
        获取每日交易蓝图
        返回: {image_url, local_path, date}
        """
        if target_date is None:
            target_date = date.today()

        try:
            logger.info(f"开始获取 {target_date} 的交易蓝图...")

            # 方法1：先尝试API接口
            api_url = "https://www.jiaoyikecha.com/ajax/guangao.php?v=8bcd6872"

            response = await self.page.evaluate(f"""
                async () => {{
                    const res = await fetch('{api_url}', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                            'X-Requested-With': 'XMLHttpRequest'
                        }},
                        body: 'path=/'
                    }});
                    return await res.json();
                }}
            """)

            if response and response.get('code') == 0:
                image_url = response.get('data', {}).get('adall', {}).get('imageUrl')

                if image_url:
                    logger.info(f"成功获取图片URL: {image_url}")

                    # 下载图片
                    local_path = await self._download_image(image_url, target_date)

                    return {
                        "image_url": image_url,
                        "local_path": str(local_path),
                        "date": target_date.strftime('%Y-%m-%d')
                    }
                else:
                    logger.warning("API返回中未找到imageUrl")

            # 方法2：如果API失败，尝试访问用户首页截图
            await self.page.goto("https://www.jiaoyikecha.com/#/user/home")
            await self.page.wait_for_timeout(3000)

            # 查找图片元素
            img_selector = "img[src*='uploadfile']"
            img_element = await self.page.query_selector(img_selector)

            if img_element:
                image_url = await img_element.get_attribute('src')
                local_path = await self._download_image(image_url, target_date)

                return {
                    "image_url": image_url,
                    "local_path": str(local_path),
                    "date": target_date.strftime('%Y-%m-%d')
                }

            logger.warning("未找到交易蓝图图片")
            return None

        except Exception as e:
            logger.error(f"获取交易蓝图失败: {e}")
            return None

    async def _download_image(self, url: str, target_date: date) -> Path:
        """下载图片到本地"""
        import httpx

        filename = f"{target_date.strftime('%Y%m%d')}.jpg"
        filepath = self.save_dir / filename

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                f.write(response.content)

        logger.info(f"图片已保存: {filepath}")
        return filepath

    async def fetch_variety_positions(self, variety_code: str) -> Optional[List[Dict]]:
        """
        获取品种的席位持仓数据
        variety_code: 如 'rb' (螺纹钢)
        """
        try:
            logger.info(f"开始获取 {variety_code} 的席位数据...")

            url = f"https://www.jiaoyikecha.com/#/variety/structure?code={variety_code}"
            await self.page.goto(url, wait_until="networkidle")
            await self.page.wait_for_timeout(3000)

            # 等待表格加载
            await self.page.wait_for_selector("table", timeout=10000)

            # 提取表格数据
            positions = await self.page.evaluate("""
                () => {
                    const rows = document.querySelectorAll('table tbody tr');
                    const data = [];

                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td');
                        if (cells.length > 0) {
                            data.push({
                                broker: cells[0]?.textContent?.trim() || '',
                                net_position: cells[1]?.textContent?.trim() || '0',
                                change: cells[2]?.textContent?.trim() || '0',
                                ratio: cells[3]?.textContent?.trim() || '0'
                            });
                        }
                    });

                    return data;
                }
            """)

            logger.info(f"成功获取 {len(positions)} 条席位数据")
            return positions

        except Exception as e:
            logger.error(f"获取席位数据失败: {e}")
            return None

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            logger.info("浏览器已关闭")


async def main():
    """测试函数"""
    spider = JiaoyiKechaSpider()

    try:
        # 初始化浏览器
        await spider.init_browser(headless=False)

        # 登录
        if await spider.login():
            # 获取交易蓝图
            blueprint = await spider.fetch_daily_blueprint()
            if blueprint:
                logger.info(f"交易蓝图数据: {json.dumps(blueprint, ensure_ascii=False, indent=2)}")

            # 获取螺纹钢席位数据
            positions = await spider.fetch_variety_positions('rb')
            if positions:
                logger.info(f"席位数据示例: {json.dumps(positions[:3], ensure_ascii=False, indent=2)}")

    finally:
        await spider.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
