"""
Openvlab 爬虫 - openvlab.cn
功能：
1. 期权合约数据 (资金流向)
2. 分时行情波动率背离
"""
import asyncio
import logging
from datetime import datetime, date
from typing import Optional, List, Dict
from playwright.async_api import async_playwright, Page, Browser
import httpx
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class OpenvlabSpider:
    """Openvlab 爬虫"""

    def __init__(self):
        self.base_url = "https://www.openvlab.cn"
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "https://www.openvlab.cn/",
                "Accept": "application/json, text/plain, */*"
            },
            timeout=30.0
        )
        self.save_dir = Path(__file__).parent.parent.parent / "openvlab" / "data"
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

    async def fetch_option_flow_data(self) -> List[Dict]:
        """
        获取期权资金流向数据
        URL: https://www.openvlab.cn/flow
        """
        try:
            logger.info("开始获取期权资金流向数据...")

            await self.page.goto(f"{self.base_url}/flow", wait_until="networkidle")
            await self.page.wait_for_timeout(3000)

            # 监听网络请求，找到数据接口
            api_data = None

            async def handle_response(response):
                nonlocal api_data
                if 'api' in response.url and response.status == 200:
                    try:
                        data = await response.json()
                        if data and isinstance(data, dict):
                            api_data = data
                            logger.info(f"捕获到API响应: {response.url}")
                    except:
                        pass

            self.page.on("response", handle_response)

            # 等待数据加载
            await self.page.wait_for_timeout(5000)

            # 如果API拦截失败，尝试从页面提取
            if not api_data:
                logger.info("API拦截失败，尝试从页面提取数据...")
                api_data = await self._extract_flow_from_page()

            if api_data:
                parsed_data = self._parse_flow_data(api_data)
                self._save_data(parsed_data, "option_flow")
                return parsed_data

            return []

        except Exception as e:
            logger.error(f"获取期权资金流向数据失败: {e}")
            return []

    async def _extract_flow_from_page(self) -> Optional[Dict]:
        """从页面DOM提取资金流向数据"""
        try:
            flow_data = await self.page.evaluate("""
                () => {
                    const rows = document.querySelectorAll('table tbody tr, .data-row, [class*="contract"]');
                    const data = [];

                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td, .cell');
                        if (cells.length >= 4) {
                            data.push({
                                contract: cells[0]?.textContent?.trim() || '',
                                flow: cells[1]?.textContent?.trim() || '',
                                volume: cells[2]?.textContent?.trim() || '',
                                change: cells[3]?.textContent?.trim() || ''
                            });
                        }
                    });

                    return { data: data };
                }
            """)

            return flow_data

        except Exception as e:
            logger.error(f"从页面提取数据失败: {e}")
            return None

    def _parse_flow_data(self, raw_data: Dict) -> List[Dict]:
        """解析资金流向数据"""
        results = []

        if isinstance(raw_data, dict) and 'data' in raw_data:
            items = raw_data.get('data', [])
        elif isinstance(raw_data, list):
            items = raw_data
        else:
            items = []

        for item in items:
            try:
                result = {
                    "contract_code": item.get("contract", item.get("code", "")),
                    "variety": self._extract_variety(item.get("contract", "")),
                    "net_flow": self._parse_number(item.get("flow", "0")),
                    "volume": self._parse_number(item.get("volume", "0")),
                    "change_ratio": self._parse_number(item.get("change", "0")),
                    "record_time": datetime.now().isoformat()
                }
                results.append(result)
            except Exception as e:
                logger.debug(f"解析单条数据失败: {e}")
                continue

        return results

    def _extract_variety(self, contract_code: str) -> str:
        """从合约代码提取品种代码"""
        import re
        # 中文品种名到代码的映射
        variety_map = {
            '沪银': 'AG', '沪金': 'AU', '沪铜': 'CU', '沪铝': 'AL',
            '沪锌': 'ZN', '沪铅': 'PB', '沪镍': 'NI', '沪锡': 'SN',
            '白糖': 'SR', '棉花': 'CF', 'PTA': 'TA', '甲醇': 'MA',
            '玻璃': 'FG', '菜粕': 'RM', '豆粕': 'M', '豆油': 'Y',
            '棕榈油': 'P', '玉米': 'C', '铁矿': 'I', '焦炭': 'J',
            '焦煤': 'JM', '螺纹': 'RB', '热卷': 'HC', '原油': 'SC',
            '橡胶': 'RU', '燃油': 'FU', '沥青': 'BU'
        }
        # 检查中文品种名
        for cn_name, code in variety_map.items():
            if cn_name in contract_code:
                return code
        # 尝试匹配英文代码（如ag, au等）
        match = re.search(r'([a-zA-Z]{1,2})(?=\d{4})', contract_code)
        if match:
            return match.group(1).upper()
        return ""

    def _parse_number(self, value: str) -> float:
        """解析数字字符串"""
        try:
            # 移除逗号和百分号
            cleaned = str(value).replace(',', '').replace('%', '').strip()
            return float(cleaned) if cleaned else 0.0
        except:
            return 0.0

    async def fetch_intraday_divergence(self) -> List[Dict]:
        """
        获取分时波动率背离数据
        URL: https://www.openvlab.cn (首页或分时页面)
        """
        try:
            logger.info("开始获取分时波动率背离数据...")

            await self.page.goto(self.base_url, wait_until="networkidle")
            await self.page.wait_for_timeout(3000)

            # 查找"分时背离"相关的链接或标签
            try:
                await self.page.click("text=分时", timeout=5000)
                await self.page.wait_for_timeout(2000)
            except:
                logger.debug("未找到'分时'按钮")

            # 提取分时背离数据
            divergence_data = await self.page.evaluate("""
                () => {
                    const items = document.querySelectorAll('.divergence-item, [class*="intraday"]');
                    const data = [];

                    items.forEach(item => {
                        const variety = item.querySelector('[class*="variety"]')?.textContent?.trim();
                        const ivRank = item.querySelector('[class*="iv"]')?.textContent?.trim();
                        const divergence = item.querySelector('[class*="diverge"]')?.textContent?.trim();

                        if (variety) {
                            data.push({
                                variety: variety,
                                iv_rank: ivRank || '',
                                divergence_type: divergence || ''
                            });
                        }
                    });

                    return data;
                }
            """)

            logger.info(f"获取到 {len(divergence_data)} 条分时背离数据")
            self._save_data(divergence_data, "intraday_divergence")
            return divergence_data

        except Exception as e:
            logger.error(f"获取分时背离数据失败: {e}")
            return []

    def _save_data(self, data: List[Dict], data_type: str):
        """保存数据到本地JSON文件"""
        today = date.today().strftime('%Y%m%d')
        filename = f"{today}_{data_type}.json"
        filepath = self.save_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"数据已保存至: {filepath}")

    async def close(self):
        """关闭资源"""
        if self.browser:
            await self.browser.close()
        await self.client.aclose()
        logger.info("资源已释放")


async def main():
    """测试函数"""
    spider = OpenvlabSpider()

    try:
        await spider.init_browser(headless=False)

        # 获取期权资金流向
        logger.info("=" * 50)
        logger.info("获取期权资金流向数据")
        logger.info("=" * 50)
        flow_data = await spider.fetch_option_flow_data()
        logger.info(f"资金流向数据共 {len(flow_data)} 条")
        if flow_data:
            logger.info(f"示例数据: {json.dumps(flow_data[:3], ensure_ascii=False, indent=2)}")

        # 获取分时波动率背离
        logger.info("=" * 50)
        logger.info("获取分时波动率背离数据")
        logger.info("=" * 50)
        divergence_data = await spider.fetch_intraday_divergence()
        logger.info(f"背离数据共 {len(divergence_data)} 条")

    finally:
        await spider.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
