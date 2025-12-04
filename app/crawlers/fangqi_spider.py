"""
方期看盘爬虫 - fxq.founderfu.com
功能：
1. 早盘数据 (每天 8:50) - REST API
2. 夜盘数据 (每天 20:50) - REST API
3. 爬取字段：breeds(品种大分类), smallbreeds(品种名称), ratingforecast(风险值), smallbreedscode(品种代码)
"""
import asyncio
import logging
from datetime import datetime, date
from typing import Optional, List, Dict
import aiohttp
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class FangqiSpider:
    """方期看盘爬虫 - 使用REST API"""

    def __init__(self):
        self.base_url = "https://fxq.founderfu.com/pc/jiandaoyun/ratingprediction/list"
        self.save_dir = Path(__file__).parent.parent.parent / "方期看盘" / "data"
        self.save_dir.mkdir(parents=True, exist_ok=True)

    async def fetch_rating_data(self, opening_type: str = "夜盘提示",
                               target_date: Optional[date] = None) -> Optional[Dict]:
        """
        获取评级预测数据
        opening_type: "夜盘提示" 或 "早盘提示"
        target_date: 目标日期,默认今天
        """
        if target_date is None:
            target_date = date.today()

        date_str = target_date.strftime('%Y-%m-%d')

        try:
            logger.info(f"开始获取{opening_type}数据 (日期: {date_str})...")

            params = {
                "openingtype": opening_type,
                "date": date_str
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'https://fxq.founderfu.com/',
                'Accept': 'application/json'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()

                        if data.get('code') == 200:
                            result = data.get('data', {})
                            logger.info(f"成功获取{opening_type}数据: 多头{result.get('manyCount')}个, 空头{result.get('shortCount')}个")
                            return result
                        else:
                            logger.error(f"API返回错误: {data.get('msg')}")
                            return None
                    else:
                        logger.error(f"HTTP请求失败: {response.status}")
                        return None

        except asyncio.TimeoutError:
            logger.error(f"请求超时: {self.base_url}")
            return None
        except Exception as e:
            logger.error(f"获取{opening_type}数据失败: {e}")
            return None

    async def fetch_morning_data(self, target_date: Optional[date] = None) -> Optional[Dict]:
        """获取早盘提示数据"""
        return await self.fetch_rating_data("早盘提示", target_date)

    async def fetch_night_data(self, target_date: Optional[date] = None) -> Optional[Dict]:
        """获取夜盘提示数据"""
        return await self.fetch_rating_data("夜盘提示", target_date)

    def parse_variety_list(self, data: Dict) -> List[Dict]:
        """
        解析品种列表数据
        返回标准化的品种数据列表
        """
        varieties = []

        # 解析多头列表
        for item in data.get('manyList', []):
            varieties.append({
                'breeds': item.get('breeds', ''),  # 品种大分类
                'smallbreeds': item.get('smallbreeds', ''),  # 品种名称
                'variety_code': item.get('smallbreedscode', '').upper(),  # 品种代码(统一大写)
                'rating': item.get('ratingforecast', ''),  # 风险值
                'direction': '多',  # 方向
                'opening_type': data.get('openingtype', ''),
                'date': data.get('date', '')
            })

        # 解析空头列表
        for item in data.get('shortList', []):
            varieties.append({
                'breeds': item.get('breeds', ''),
                'smallbreeds': item.get('smallbreeds', ''),
                'variety_code': item.get('smallbreedscode', '').upper(),
                'rating': item.get('ratingforecast', ''),
                'direction': '空',
                'opening_type': data.get('openingtype', ''),
                'date': data.get('date', '')
            })

        logger.info(f"解析得到 {len(varieties)} 个品种数据")
        return varieties

    def _save_data(self, data: Dict, opening_type: str):
        """保存原始数据到本地JSON文件"""
        today = date.today().strftime('%Y%m%d')
        filename = f"{today}_{opening_type}.json"
        filepath = self.save_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"数据已保存至: {filepath}")

    async def init_browser(self, headless: bool = True):
        """兼容接口 - REST API不需要浏览器"""
        logger.info("方期看盘使用REST API,无需浏览器初始化")

    async def close(self):
        """兼容接口 - REST API无需关闭"""
        logger.info("方期看盘API调用完成")


async def main():
    """测试函数"""
    spider = FangqiSpider()

    try:
        # 获取夜盘数据
        logger.info("=" * 50)
        logger.info("获取夜盘提示数据")
        logger.info("=" * 50)
        night_data = await spider.fetch_night_data()

        if night_data:
            spider._save_data(night_data, "夜盘提示")
            varieties = spider.parse_variety_list(night_data)
            logger.info(f"解析后的品种数据示例 (前3个):")
            for v in varieties[:3]:
                logger.info(f"  {v}")

        # 获取早盘数据
        logger.info("=" * 50)
        logger.info("获取早盘提示数据")
        logger.info("=" * 50)
        morning_data = await spider.fetch_morning_data()

        if morning_data:
            spider._save_data(morning_data, "早盘提示")
            varieties = spider.parse_variety_list(morning_data)
            logger.info(f"解析后的品种数据示例 (前3个):")
            for v in varieties[:3]:
                logger.info(f"  {v}")

    finally:
        await spider.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
