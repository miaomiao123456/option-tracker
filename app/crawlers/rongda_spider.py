"""
融达数据分析家爬虫 - dt.rongdaqh.com
功能：
1. 找非常明显的 contango 和 back 结构品种
2. 期限结构分析
"""
import asyncio
import logging
from datetime import datetime, date
from typing import Optional, List, Dict
from playwright.async_api import async_playwright, Page, Browser
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class RongdaSpider:
    """融达数据分析家爬虫"""

    def __init__(self):
        self.base_url = "https://dt.rongdaqh.com"
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.save_dir = Path(__file__).parent.parent.parent / "融达数据" / "data"
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

    async def fetch_market_structure(self) -> List[Dict]:
        """
        获取市场期限结构数据
        URL: https://dt.rongdaqh.com/analysis_futures_markets/market_structure
        """
        try:
            logger.info("开始获取市场期限结构数据...")

            url = f"{self.base_url}/analysis_futures_markets/market_structure"
            await self.page.goto(url, wait_until="networkidle")
            await self.page.wait_for_timeout(5000)

            # 提取期限结构数据
            structure_data = await self.page.evaluate("""
                () => {
                    const rows = document.querySelectorAll('table tbody tr, .structure-row, [class*="variety"]');
                    const data = [];

                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td, .cell');
                        if (cells.length > 0) {
                            const variety = cells[0]?.textContent?.trim() || '';
                            const structure = cells[1]?.textContent?.trim() || '';
                            const strength = cells[2]?.textContent?.trim() || '';
                            const spread = cells[3]?.textContent?.trim() || '';

                            if (variety) {
                                data.push({
                                    variety: variety,
                                    structure: structure,
                                    strength: strength,
                                    spread: spread
                                });
                            }
                        }
                    });

                    return data;
                }
            """)

            # 过滤出明显的 contango 和 back 结构
            filtered_data = self._filter_strong_structures(structure_data)

            logger.info(f"获取到 {len(structure_data)} 条期限结构数据")
            logger.info(f"其中明显结构 {len(filtered_data)} 条")

            self._save_data(filtered_data, "market_structure")
            return filtered_data

        except Exception as e:
            logger.error(f"获取市场结构数据失败: {e}")
            return []

    def _filter_strong_structures(self, data: List[Dict]) -> List[Dict]:
        """
        过滤出明显的期限结构
        判断标准：
        1. contango: 远月合约价格 > 近月合约价格，且价差明显
        2. back (backwardation): 近月合约价格 > 远月合约价格，且价差明显
        """
        filtered = []

        for item in data:
            structure = item.get('structure', '').lower()
            strength = item.get('strength', '')
            spread = item.get('spread', '')

            # 判断结构类型
            is_contango = 'contango' in structure or '升水' in structure or '正向' in structure
            is_back = 'back' in structure or '贴水' in structure or '反向' in structure

            # 判断强度
            is_strong = (
                    '强' in strength or
                    '明显' in strength or
                    'strong' in strength.lower() or
                    self._is_large_spread(spread)
            )

            if (is_contango or is_back) and is_strong:
                item['structure_type'] = 'contango' if is_contango else 'back'
                item['is_significant'] = True
                filtered.append(item)

        return filtered

    def _is_large_spread(self, spread_str: str) -> bool:
        """判断价差是否够大"""
        try:
            # 提取数字
            import re
            numbers = re.findall(r'-?\d+\.?\d*', spread_str)
            if numbers:
                spread_value = abs(float(numbers[0]))
                # 假设价差大于50认为明显（具体阈值可调整）
                return spread_value > 50
        except:
            pass
        return False

    async def fetch_variety_structure_detail(self, variety: str) -> Optional[Dict]:
        """
        获取单个品种的详细期限结构
        variety: 品种代码，如 'rb' (螺纹钢)
        """
        try:
            logger.info(f"开始获取{variety}的详细期限结构...")

            # 构建URL（可能需要根据实际情况调整）
            url = f"{self.base_url}/analysis_futures_markets/market_structure?variety={variety}"
            await self.page.goto(url, wait_until="networkidle")
            await self.page.wait_for_timeout(3000)

            # 提取合约价格列表
            contracts_data = await self.page.evaluate("""
                () => {
                    const contracts = document.querySelectorAll('.contract-item, [class*="contract"]');
                    const data = [];

                    contracts.forEach(contract => {
                        const code = contract.querySelector('[class*="code"]')?.textContent?.trim();
                        const price = contract.querySelector('[class*="price"]')?.textContent?.trim();
                        const volume = contract.querySelector('[class*="volume"]')?.textContent?.trim();

                        if (code && price) {
                            data.push({
                                contract_code: code,
                                price: price,
                                volume: volume || ''
                            });
                        }
                    });

                    return data;
                }
            """)

            if contracts_data:
                # 计算期限结构
                structure_info = self._analyze_structure(contracts_data)

                result = {
                    "variety": variety,
                    "contracts": contracts_data,
                    "structure_analysis": structure_info,
                    "record_time": datetime.now().isoformat()
                }

                return result

            return None

        except Exception as e:
            logger.error(f"获取{variety}详细结构失败: {e}")
            return None

    def _analyze_structure(self, contracts: List[Dict]) -> Dict:
        """
        分析合约列表的期限结构
        """
        if len(contracts) < 2:
            return {"type": "unknown", "reason": "合约数量不足"}

        try:
            # 按合约月份排序
            sorted_contracts = sorted(contracts, key=lambda x: x.get('contract_code', ''))

            # 比较近月和远月价格
            near_price = float(sorted_contracts[0].get('price', '0').replace(',', ''))
            far_price = float(sorted_contracts[-1].get('price', '0').replace(',', ''))

            spread = far_price - near_price
            spread_ratio = (spread / near_price * 100) if near_price != 0 else 0

            if spread > 0:
                structure_type = "contango"
                description = f"升水结构，远月比近月高 {spread:.2f} 元 ({spread_ratio:.2f}%)"
            elif spread < 0:
                structure_type = "back"
                description = f"贴水结构，近月比远月高 {abs(spread):.2f} 元 ({abs(spread_ratio):.2f}%)"
            else:
                structure_type = "flat"
                description = "平水结构"

            return {
                "type": structure_type,
                "spread": spread,
                "spread_ratio": spread_ratio,
                "description": description,
                "is_significant": abs(spread_ratio) > 5  # 价差超过5%认为明显
            }

        except Exception as e:
            logger.error(f"分析期限结构失败: {e}")
            return {"type": "error", "reason": str(e)}

    def _save_data(self, data: List[Dict], data_type: str):
        """保存数据到本地JSON文件"""
        today = date.today().strftime('%Y%m%d')
        filename = f"{today}_{data_type}.json"
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
    spider = RongdaSpider()

    try:
        await spider.init_browser(headless=False)

        # 获取市场期限结构
        logger.info("=" * 50)
        logger.info("获取市场期限结构数据")
        logger.info("=" * 50)
        structure_data = await spider.fetch_market_structure()
        logger.info(f"期限结构数据共 {len(structure_data)} 条")

        if structure_data:
            logger.info(f"明显结构示例: {json.dumps(structure_data[:3], ensure_ascii=False, indent=2)}")

            # 获取第一个品种的详细数据
            if structure_data:
                first_variety = structure_data[0].get('variety', '')
                if first_variety:
                    detail = await spider.fetch_variety_structure_detail(first_variety)
                    if detail:
                        logger.info(f"详细结构: {json.dumps(detail, ensure_ascii=False, indent=2)}")

    finally:
        await spider.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
