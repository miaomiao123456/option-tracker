# -*- coding: utf-8 -*-
"""
交易可查席位数据爬虫 (基于 requests + ddddocr)
"""
import requests
import logging
import time
from datetime import date, datetime
from typing import Dict, List, Optional
import json

# Pillow 兼容性补丁 - 修复 Pillow 10.0+ 移除 ANTIALIAS 的问题
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS

import ddddocr

logger = logging.getLogger(__name__)


class JiaoyikechaSpider:
    """交易可查爬虫"""

    # 预设的浏览器cookie (从浏览器登录后获取，定期更新)
    PRESET_COOKIES = {
        'remember': '202c963771fa356d45067587ea46dea6',
        'PHPSESSID': '90ce1eb19a6cb7e7c112b4ddebb6a6a9'
    }

    def __init__(self, use_preset_cookie: bool = True):
        self.base_url = "https://www.jiaoyikecha.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://www.jiaoyikecha.com/position.html',
            'Origin': 'https://www.jiaoyikecha.com'
        })

        # 优先使用预设cookie
        self.use_preset_cookie = use_preset_cookie
        if use_preset_cookie:
            for name, value in self.PRESET_COOKIES.items():
                self.session.cookies.set(name, value)
            self.is_logged_in = True
            logger.info("使用预设cookie初始化")

        # OCR识别器 (仅在需要登录时初始化)
        self._ocr = None

        # 登录凭证
        self.username = "18321399574"
        self.password = "yi2013405"

    @property
    def ocr(self):
        """延迟初始化OCR识别器"""
        if self._ocr is None:
            self._ocr = ddddocr.DdddOcr()
        return self._ocr

    def get_captcha(self) -> str:
        """获取验证码并识别"""
        try:
            captcha_url = f"{self.base_url}/captcha.php?t={int(time.time() * 1000)}"
            response = self.session.get(captcha_url, timeout=10)

            if response.status_code != 200:
                logger.error(f"获取验证码失败: HTTP {response.status_code}")
                return ""

            captcha_text = self.ocr.classification(response.content)
            logger.info(f"验证码识别结果: {captcha_text}")
            return captcha_text.strip()

        except Exception as e:
            logger.error(f"验证码识别失败: {e}")
            return ""

    def login(self) -> bool:
        """登录交易可查"""
        try:
            captcha = self.get_captcha()
            if not captcha:
                logger.error("验证码识别失败,无法登录")
                return False

            login_url = f"{self.base_url}/ajax/user_login.php"
            data = {
                'username': self.username,
                'password': self.password,
                'vercode': captcha,
                'remember': 'on'
            }

            response = self.session.post(login_url, data=data, timeout=10)

            if response.status_code != 200:
                logger.error(f"登录请求失败: HTTP {response.status_code}")
                return False

            result = response.json()
            logger.info(f"登录响应: {result}")

            # 登录成功条件: code == 0 或 error == 0
            if result.get('code') == 0 or result.get('error') == 0 or result.get('success'):
                self.is_logged_in = True
                logger.info("✅ 登录成功")
                return True
            else:
                error_msg = result.get('msg', '未知错误')
                logger.error(f"登录失败: {error_msg}")

                if '验证码' in error_msg or 'vercode' in error_msg.lower():
                    logger.info("验证码错误,尝试重新登录...")
                    time.sleep(1)
                    return self.login()

                return False

        except Exception as e:
            logger.error(f"登录异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def ensure_logged_in(self) -> bool:
        """确保已登录状态"""
        if not self.is_logged_in:
            return self.login()
        return True

    def fetch_position_data(
        self,
        variety: str,
        contract_code: str,
        query_date: Optional[date] = None
    ) -> Dict:
        """获取品种的持仓席位数据"""
        if not self.ensure_logged_in():
            return {
                "success": False,
                "error": "登录失败,无法获取数据"
            }

        try:
            if query_date is None:
                query_date = date.today()

            date_str = query_date.strftime('%Y-%m-%d')

            url = f"{self.base_url}/ajax/variety_position.php?v=f0799170"
            data = {
                'variety': variety,
                'code': contract_code,
                'date': date_str
            }

            logger.info(f"正在获取 {variety}({contract_code}) {date_str} 的席位数据...")

            response = self.session.post(url, data=data, timeout=10)

            if response.status_code != 200:
                logger.error(f"请求失败: HTTP {response.status_code}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                }

            result = response.json()

            if result.get('error') == -1 or '登录' in str(result.get('msg', '')):
                logger.warning("登录已过期,重新登录...")
                self.is_logged_in = False
                if self.login():
                    return self.fetch_position_data(variety, contract_code, query_date)
                else:
                    return {
                        "success": False,
                        "error": "重新登录失败"
                    }

            logger.info(f"✅ 成功获取 {variety} 席位数据")
            logger.debug(f"原始返回数据: {json.dumps(result, ensure_ascii=False, indent=2)}")

            parsed_data = self._parse_position_data(result, variety, contract_code, date_str)
            return parsed_data

        except Exception as e:
            logger.error(f"获取席位数据失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    def _parse_position_data(
        self,
        raw_data: Dict,
        variety: str,
        contract_code: str,
        date_str: str
    ) -> Dict:
        """解析席位数据"""
        try:
            logger.info(f"开始解析数据,raw_data结构: {list(raw_data.keys())}")

            # 检查多种可能的响应结构
            if raw_data.get('code') != 0 and raw_data.get('error') != 0:
                return {
                    "success": False,
                    "error": raw_data.get('msg', '数据解析失败'),
                    "raw_data": raw_data
                }

            data = raw_data.get('data', {})

            # 解析多头持仓 (buy)
            long_positions = []
            long_list = data.get('buy', [])
            for i, item in enumerate(long_list[:20]):
                long_positions.append({
                    "rank": i + 1,
                    "broker": item.get('broker', ''),
                    "volume": item.get('buy', 0),
                    "change": item.get('buy_chge', 0),
                    "net_position": item.get('net_position', 0)
                })

            # 解析空头持仓 (ss)
            short_positions = []
            short_list = data.get('ss', [])
            for i, item in enumerate(short_list[:20]):
                short_positions.append({
                    "rank": i + 1,
                    "broker": item.get('broker', ''),
                    "volume": item.get('ss', 0),
                    "change": item.get('ss_chge', 0),
                    "net_position": item.get('net_position', 0)
                })

            long_top5_total = sum(p['volume'] for p in long_positions[:5])
            short_top5_total = sum(p['volume'] for p in short_positions[:5])

            return {
                "success": True,
                "variety": variety,
                "contract_code": contract_code,
                "date": date_str,
                "long_positions": long_positions,
                "short_positions": short_positions,
                "long_top5_total": long_top5_total,
                "short_top5_total": short_top5_total,
                "raw_data": data
            }

        except Exception as e:
            logger.error(f"解析席位数据失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"数据解析失败: {str(e)}",
                "raw_data": raw_data
            }

    def fetch_full_position_data(
        self,
        variety: str,
        contract_code: str,
        query_date: Optional[date] = None
    ) -> Dict:
        """获取完整的持仓数据,包括历史趋势数据"""
        if not self.ensure_logged_in():
            return {
                "success": False,
                "error": "登录失败,无法获取数据"
            }

        try:
            if query_date is None:
                query_date = date.today()

            date_str = query_date.strftime('%Y-%m-%d')

            url = f"{self.base_url}/ajax/variety_position.php?v=f0799170"
            data = {
                'variety': variety,
                'code': contract_code,
                'date': date_str
            }

            logger.info(f"正在获取 {variety}({contract_code}) {date_str} 的完整席位数据...")

            response = self.session.post(url, data=data, timeout=10)

            if response.status_code != 200:
                logger.error(f"请求失败: HTTP {response.status_code}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                }

            result = response.json()

            if result.get('error') == -1 or '登录' in str(result.get('msg', '')):
                logger.warning("登录已过期,重新登录...")
                self.is_logged_in = False
                if self.login():
                    return self.fetch_full_position_data(variety, contract_code, query_date)
                else:
                    return {
                        "success": False,
                        "error": "重新登录失败"
                    }

            # 检查响应结构
            if result.get('code') != 0:
                return {
                    "success": False,
                    "error": result.get('msg', '数据获取失败')
                }

            data_obj = result.get('data', {})

            logger.info(f"✅ 成功获取 {variety} 完整席位数据")

            return {
                "success": True,
                "variety": variety,
                "contract_code": contract_code,
                "date": date_str,
                "data": data_obj
            }

        except Exception as e:
            logger.error(f"获取完整席位数据失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }


def test_jiaoyikecha_spider():
    """测试交易可查爬虫"""
    logging.basicConfig(
        level=logging.DEBUG,  # 改为DEBUG级别
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    spider = JiaoyikechaSpider()

    logger.info("=" * 60)
    logger.info("测试:登录交易可查")
    logger.info("=" * 60)

    if spider.login():
        logger.info("✅ 登录成功")
    else:
        logger.error("❌ 登录失败")
        return

    logger.info("\n" + "=" * 60)
    logger.info("测试:获取螺纹钢席位数据")
    logger.info("=" * 60)

    result = spider.fetch_position_data(
        variety="螺纹钢",
        contract_code="rb2605",
        query_date=date.today()
    )

    if result.get('success'):
        logger.info(f"\n✅ 成功获取数据:")
        logger.info(f"  品种: {result['variety']}")
        logger.info(f"  合约: {result['contract_code']}")
        logger.info(f"  日期: {result['date']}")
        logger.info(f"  多头前5合计: {result['long_top5_total']}")
        logger.info(f"  空头前5合计: {result['short_top5_total']}")
        logger.info(f"\n  多头前5席位:")
        for pos in result['long_positions'][:5]:
            logger.info(f"    {pos['rank']}. {pos['broker']}: {pos['volume']} ({pos['change']:+d})")
        logger.info(f"\n  空头前5席位:")
        for pos in result['short_positions'][:5]:
            logger.info(f"    {pos['rank']}. {pos['broker']}: {pos['volume']} ({pos['change']:+d})")
    else:
        logger.error(f"❌ 获取数据失败: {result.get('error')}")
        logger.info(f"原始响应: {result}")


if __name__ == "__main__":
    test_jiaoyikecha_spider()
