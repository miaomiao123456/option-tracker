"""
方期看盘爬虫 - fxq.founderfu.com
功能：
1. 早盘数据 (每天 8:50)
2. 夜盘数据 (每天 20:50)
3. 爬取内容：方向、品种、强度、总结、重要资讯、市场逻辑、交易策略
"""
import asyncio
import logging
from datetime import datetime, date
from typing import Optional, List, Dict
from playwright.async_api import async_playwright, Page, Browser
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class FangqiSpider:
    """方期看盘爬虫"""

    def __init__(self):
        self.base_url = "https://fxq.founderfu.com/fangzheng-forward/qiweih5/#/"
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.save_dir = Path(__file__).parent.parent.parent / "方期看盘" / "data"
        self.save_dir.mkdir(parents=True, exist_ok=True)

    async def init_browser(self, headless: bool = True):
        """初始化浏览器"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=headless,
            args=['--no-sandbox']
        )
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        self.page = await context.new_page()
        logger.info("浏览器初始化成功")

    async def fetch_market_data(self, opening_type: str = "夜盘提示") -> List[Dict]:
        """
        获取盘前数据列表
        opening_type: "夜盘提示" 或 "早盘提示"
        """
        try:
            logger.info(f"开始获取{opening_type}数据...")

            # 访问主页
            await self.page.goto(self.base_url, wait_until="networkidle")
            await self.page.wait_for_timeout(3000)

            # 点击对应的标签页
            if opening_type == "早盘提示":
                await self.page.click("text=早盘提示")
            else:
                await self.page.click("text=夜盘提示")

            await self.page.wait_for_timeout(2000)

            # 提取品种列表数据
            varieties_data = await self.page.evaluate("""
                () => {
                    const cards = document.querySelectorAll('.variety-card, .breed-item, [class*="variety"]');
                    const data = [];

                    cards.forEach(card => {
                        const variety = card.querySelector('[class*="breed"], .variety-name')?.textContent?.trim();
                        const direction = card.querySelector('[class*="direction"], .trend')?.textContent?.trim();
                        const strength = card.querySelector('[class*="strength"], .level')?.textContent?.trim();

                        if (variety) {
                            data.push({
                                variety: variety,
                                direction: direction || '',
                                strength: strength || ''
                            });
                        }
                    });

                    return data;
                }
            """)

            logger.info(f"获取到 {len(varieties_data)} 个品种的{opening_type}数据")
            return varieties_data

        except Exception as e:
            logger.error(f"获取{opening_type}数据失败: {e}")
            return []

    async def fetch_variety_detail(self, variety: str, target_date: Optional[date] = None,
                                   opening_type: str = "夜盘提示") -> Optional[Dict]:
        """
        获取单个品种的详细信息
        variety: 品种名称，如"热卷"
        target_date: 目标日期
        opening_type: "夜盘提示" 或 "早盘提示"
        """
        if target_date is None:
            target_date = date.today()

        try:
            logger.info(f"开始获取{variety}的详细数据...")

            # 构建详情页URL
            # 示例: https://fxq.founderfu.com/fangzheng-forward/qiweih5/#/pages/openQuotation/quotationDetail
            # 参数: breeds=热卷&date=2025-11-21&openingtype=夜盘提示

            date_str = target_date.strftime('%Y-%m-%d')
            weekday = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][target_date.weekday()]

            params = {
                "breeds": variety,
                "date": date_str,
                "week": weekday,
                "openingtype": opening_type,
                "deptId": "",
                "brokerId": "",
                "brokerName": "",
                "wxPhone": "",
                "fz_source": ""
            }

            # 将参数转换为URL编码的JSON
            import urllib.parse
            param_str = urllib.parse.quote(json.dumps(params, ensure_ascii=False))

            detail_url = f"{self.base_url}pages/openQuotation/quotationDetail?param={param_str}"

            await self.page.goto(detail_url, wait_until="networkidle")
            await self.page.wait_for_timeout(3000)

            # 提取详细信息
            detail_data = await self.page.evaluate("""
                () => {
                    const getText = (selector) => {
                        const el = document.querySelector(selector);
                        return el ? el.textContent.trim() : '';
                    };

                    return {
                        summary: getText('[class*="summary"], .overview'),
                        important_news: getText('[class*="important"], [class*="news"]'),
                        market_logic: getText('[class*="logic"], [class*="analysis"]'),
                        trading_strategy: getText('[class*="strategy"], [class*="suggestion"]')
                    };
                }
            """)

            result = {
                "variety": variety,
                "date": date_str,
                "opening_type": opening_type,
                **detail_data
            }

            logger.info(f"成功获取{variety}详细数据")
            return result

        except Exception as e:
            logger.error(f"获取{variety}详细数据失败: {e}")
            return None

    async def fetch_all_varieties_detail(self, opening_type: str = "夜盘提示") -> List[Dict]:
        """
        获取所有品种的详细数据
        """
        # 先获取品种列表
        varieties = await self.fetch_market_data(opening_type)

        if not varieties:
            logger.warning("未获取到品种列表")
            return []

        all_details = []

        for variety_item in varieties:
            variety_name = variety_item.get('variety', '')

            if not variety_name:
                continue

            # 获取详细数据
            detail = await self.fetch_variety_detail(variety_name, opening_type=opening_type)

            if detail:
                # 合并基础数据和详细数据
                merged_data = {
                    **variety_item,
                    **detail
                }
                all_details.append(merged_data)

            # 延迟避免请求过快
            await asyncio.sleep(1)

        # 保存到本地
        self._save_data(all_details, opening_type)

        return all_details

    def _save_data(self, data: List[Dict], opening_type: str):
        """保存数据到本地JSON文件"""
        today = date.today().strftime('%Y%m%d')
        filename = f"{today}_{opening_type}.json"
        filepath = self.save_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"数据已保存至: {filepath}")

    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            logger.info("浏览器已关闭")


async def main():
    """测试函数"""
    spider = FangqiSpider()

    try:
        await spider.init_browser(headless=False)

        # 获取夜盘数据
        logger.info("=" * 50)
        logger.info("获取夜盘提示数据")
        logger.info("=" * 50)
        night_data = await spider.fetch_all_varieties_detail(opening_type="夜盘提示")
        logger.info(f"夜盘数据共 {len(night_data)} 条")

        # 获取早盘数据
        logger.info("=" * 50)
        logger.info("获取早盘提示数据")
        logger.info("=" * 50)
        morning_data = await spider.fetch_all_varieties_detail(opening_type="早盘提示")
        logger.info(f"早盘数据共 {len(morning_data)} 条")

    finally:
        await spider.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
