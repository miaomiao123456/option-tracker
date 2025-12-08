"""
期限结构数据更新脚本 - 多数据源支持
每天15:05运行,获取当日期货各品种合约的收盘数据

数据源优先级:
1. AKShare新浪数据 (主要)
2. 直接爬取交易所网站 (备用)
3. 本地缓存数据 (降级)
"""
import akshare as ak
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
import logging
import time
import re
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FuturesDataFetcher:
    """期货数据获取器 - 支持多数据源"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def fetch_contract_data_akshare(self, contract_code):
        """
        方法1: 使用AKShare新浪数据 - 使用futures_main_sina接口
        """
        try:
            # futures_main_sina 可以获取具体合约的历史数据
            df = ak.futures_main_sina(symbol=contract_code)
            if not df.empty and len(df) > 0:
                latest = df.iloc[-1]
                # 使用收盘价作为结算价
                return {
                    "symbol": contract_code,
                    "price": float(latest['收盘价']),
                    "volume": int(latest['成交量']),
                    "open_interest": int(latest['持仓量']),
                    "date": str(latest['日期']),
                    "source": "akshare_sina_main"
                }
        except Exception as e:
            logger.warning(f"AKShare失败 {contract_code}: {str(e)[:100]}")
        return None

    def fetch_contract_data_exchange(self, variety_code, year, month):
        """
        方法2: 直接从交易所网站获取数据 (备用数据源)

        品种所属交易所:
        - M, C, A, Y, P, I, L, V, PP, J, JM, EG, EB, CS, JD, RR, LH, B: 大商所 (DCE)
        - RB, CU, AL, HC, AU, AG, ZN, PB, NI, SN, FU, BU, RU, SP: 上期所 (SHFE)
        - SR, CF, TA, OI, MA, FG, RM, ZC, SF, SM, UR, SA, PF, PK, AP, CJ, PX, CY: 郑商所 (CZCE)
        """
        contract_code = f"{variety_code}{year}{month}"

        # 根据品种确定交易所
        dce_varieties = ['M', 'C', 'A', 'B', 'Y', 'P', 'I', 'L', 'V', 'PP', 'J', 'JM',
                        'EG', 'EB', 'CS', 'JD', 'RR', 'LH']  # 大商所
        shfe_varieties = ['RB', 'CU', 'AL', 'HC', 'AU', 'AG', 'ZN', 'PB', 'NI', 'SN',
                         'FU', 'BU', 'RU', 'SP', 'SC', 'LU', 'NR', 'SS']  # 上期所+能源中心
        czce_varieties = ['SR', 'CF', 'TA', 'OI', 'MA', 'FG', 'RM', 'ZC', 'SF', 'SM',
                         'UR', 'SA', 'PF', 'PK', 'AP', 'CJ', 'PX', 'CY', 'SH', 'PL', 'PR']  # 郑商所

        try:
            if variety_code in czce_varieties:
                return self._fetch_from_czce(variety_code, year, month)
            elif variety_code in dce_varieties:
                return self._fetch_from_dce(variety_code, year, month)
            elif variety_code in shfe_varieties:
                return self._fetch_from_shfe(variety_code, year, month)
        except Exception as e:
            logger.debug(f"交易所API失败 {contract_code}: {e}")

        return None

    def _fetch_from_czce(self, variety_code, year, month):
        """从郑商所获取数据"""
        # 郑商所使用3位数字格式：品种代码 + 年份最后1位 + 月份2位
        # 例如：SR2601 → SR601
        czce_contract_code = f"{variety_code}{year[1:]}{month}"
        contract_code = f"{variety_code}{year}{month}"  # 标准格式用于返回

        try:
            # 尝试最近10天的数据（跳过周末和节假日）
            # 从最近的工作日开始尝试
            for days_ago in range(1, 11):
                current_date = datetime.now() - timedelta(days=days_ago)
                # 跳过周六(5)和周日(6)
                if current_date.weekday() in [5, 6]:
                    continue

                date_str = current_date.strftime("%Y%m%d")
                url = f"http://www.czce.com.cn/cn/DFSStaticFiles/Future/{date_str[:4]}/{date_str}/FutureDataDaily.htm"

                try:
                    response = self.session.get(url, timeout=5)
                    if response.status_code != 200:
                        continue

                    response.encoding = 'utf-8'

                    # 解析HTML表格
                    soup = BeautifulSoup(response.text, 'html.parser')
                    table = soup.find('table')
                    if not table:
                        continue

                    rows = table.find_all('tr')
                    for row in rows[1:]:  # 跳过表头
                        cols = row.find_all('td')
                        if len(cols) >= 11:
                            code = cols[0].text.strip()
                            # 匹配合约代码（郑商所格式：如SR601）
                            if code == czce_contract_code:
                                try:
                                    settle_price = float(cols[6].text.strip().replace(',', ''))
                                    volume = int(cols[9].text.strip().replace(',', ''))
                                    open_interest = int(cols[10].text.strip().replace(',', ''))

                                    if settle_price > 0:
                                        return {
                                            "symbol": contract_code,
                                            "price": settle_price,
                                            "volume": volume,
                                            "open_interest": open_interest,
                                            "date": date_str,
                                            "source": "czce"
                                        }
                                except (ValueError, IndexError):
                                    continue
                except:
                    continue

            return None

        except Exception as e:
            logger.debug(f"郑商所获取失败 {contract_code}: {e}")
            return None

    def _fetch_from_dce(self, variety_code, year, month):
        """从大商所获取数据"""
        contract_code = f"{variety_code}{year}{month}"

        try:
            # 尝试最近10天的数据（跳过周末和节假日）
            for days_ago in range(1, 11):
                current_date = datetime.now() - timedelta(days=days_ago)

                # 跳过周六(5)和周日(6)
                if current_date.weekday() in [5, 6]:
                    continue

                date_str = current_date.strftime("%Y%m%d")
                url = f"http://www.dce.com.cn/publicweb/quotesdata/exportDayQuotesChData.html"

                try:
                    # 大商所需要POST请求
                    data = {
                        'dayQuotes.variety': 'all',
                        'dayQuotes.trade_type': '0',
                        'year': date_str[:4],
                        'month': str(int(date_str[4:6]) - 1),  # 月份从0开始
                        'day': date_str[6:8]
                    }

                    response = self.session.post(url, data=data, timeout=10)

                    if response.status_code != 200:
                        continue

                    response.encoding = 'utf-8'

                    # 解析CSV格式数据
                    lines = response.text.split('\n')
                    for line in lines:
                        if contract_code in line:
                            parts = line.split(',')
                            if len(parts) >= 12:
                                try:
                                    settle_price = float(parts[5].strip().replace(',', ''))
                                    volume = int(parts[10].strip().replace(',', ''))
                                    open_interest = int(parts[11].strip().replace(',', ''))

                                    if settle_price > 0:
                                        return {
                                            "symbol": contract_code,
                                            "price": settle_price,
                                            "volume": volume,
                                            "open_interest": open_interest,
                                            "date": date_str,
                                            "source": "dce"
                                        }
                                except (ValueError, IndexError):
                                    continue
                except:
                    continue

            return None

        except Exception as e:
            logger.debug(f"大商所获取失败 {contract_code}: {e}")
            return None

    def _fetch_from_shfe(self, variety_code, year, month):
        """从上期所获取数据"""
        contract_code = f"{variety_code.lower()}{year}{month}"

        try:
            # 尝试最近10天的数据（跳过周末和节假日）
            for days_ago in range(1, 11):
                current_date = datetime.now() - timedelta(days=days_ago)

                # 跳过周六(5)和周日(6)
                if current_date.weekday() in [5, 6]:
                    continue

                date_str = current_date.strftime("%Y%m%d")
                url = f"http://www.shfe.com.cn/data/dailydata/kx/kx{date_str}.dat"

                try:
                    response = self.session.get(url, timeout=10)

                    if response.status_code != 200:
                        continue

                    data = response.json()

                    # 查找对应合约
                    for item in data.get('o_curinstrument', []):
                        if item.get('PRODUCTID', '').lower() == contract_code.lower():
                            try:
                                settle_price = float(item.get('SETTLEMENTPRICE', 0))
                                volume = int(item.get('VOLUME', 0))
                                open_interest = int(item.get('OPENINTEREST', 0))

                                if settle_price > 0:
                                    return {
                                        "symbol": variety_code + year + month,
                                        "price": settle_price,
                                        "volume": volume,
                                        "open_interest": open_interest,
                                        "date": date_str,
                                        "source": "shfe"
                                    }
                            except (ValueError, KeyError):
                                continue
                except:
                    continue

            return None

        except Exception as e:
            logger.debug(f"上期所获取失败 {contract_code}: {e}")
            return None

    def fetch_contract_data(self, variety_code, year, month):
        """
        获取合约数据 - 使用AKShare futures_main_sina接口
        """
        contract_code = f"{variety_code}{year}{month}"

        # 使用AKShare futures_main_sina接口（可用）
        data = self.fetch_contract_data_akshare(contract_code)
        if data:
            return data

        # 备用: 交易所官网（目前也有问题，但保留作为降级方案）
        data = self.fetch_contract_data_exchange(variety_code, year, month)
        if data:
            return data

        return None


def get_active_contracts_for_variety(variety_code: str, years: list = None, fetcher: FuturesDataFetcher = None):
    """
    获取指定品种当前活跃的合约数据

    不再提前过滤"过期"合约，而是尝试获取所有合约，
    让数据源决定哪些合约有数据。这样可以获取到那些
    虽然接近交割但仍在交易的主力合约。

    Args:
        variety_code: 品种代码,如 M, C, RB等
        years: 合约年份后两位列表,如 ["25", "26"] 表示2025年和2026年
        fetcher: 数据获取器实例

    Returns:
        list: 有数据的合约列表
    """
    if fetcher is None:
        fetcher = FuturesDataFetcher()

    if years is None:
        years = ["25", "26"]  # 默认获取2025和2026年

    # 获取所有月份合约(01-12月)
    months = [f"{i:02d}" for i in range(1, 13)]
    contracts = []
    failed_count = 0

    for year in years:
        for month in months:
            contract_code = f"{variety_code}{year}{month}"

            try:
                # 使用多数据源获取器
                data = fetcher.fetch_contract_data(variety_code, year, month)

                # 过滤已退市的合约：只保留最近7天有数据的合约
                if data:
                    from datetime import datetime, timedelta
                    try:
                        data_date = datetime.strptime(str(data['date']), '%Y-%m-%d')
                        days_old = (datetime.now() - data_date).days

                        # 只保留最近7天有数据的合约（说明还在交易）
                        if days_old <= 7:
                            contracts.append({
                                "symbol": data['symbol'],
                                "month": f"{year}{month}",
                                "price": data['price'],
                                "volume": data['volume'],
                                "open_interest": data['open_interest'],
                                "date": data['date'],
                                "source": data.get('source', 'unknown')
                            })
                            logger.info(f"✓ {contract_code}: 价格={data['price']}, 持仓={data['open_interest']}, 数据={data['date']} [{data.get('source', '未知')}]")
                        else:
                            logger.debug(f"⊗ {contract_code}: 数据过旧({days_old}天前), 已退市")
                            failed_count += 1
                    except:
                        # 如果日期解析失败，保留数据
                        contracts.append({
                            "symbol": data['symbol'],
                            "month": f"{year}{month}",
                            "price": data['price'],
                            "volume": data['volume'],
                            "open_interest": data['open_interest'],
                            "date": data['date'],
                            "source": data.get('source', 'unknown')
                        })
                        logger.info(f"✓ {contract_code}: 价格={data['price']}, 持仓={data['open_interest']} [{data.get('source', '未知')}]")
                else:
                    failed_count += 1

                # 避免请求过快
                time.sleep(0.1)

            except Exception as e:
                failed_count += 1
                logger.warning(f"✗ {contract_code}: {str(e)[:50]}")
                continue

    logger.info(f"{variety_code}: 成功{len(contracts)}个, 失败{failed_count}个")
    return contracts


def load_cache_data():
    """加载缓存数据"""
    cache_file = Path(__file__).parent.parent / "data" / "term_structure_data.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data:  # 确保不是空字典
                    logger.info(f"加载缓存数据: {len(data)}个品种")
                    return data
        except Exception as e:
            logger.warning(f"加载缓存失败: {e}")
    return {}


def classify_term_structure(contracts, market_structure):
    """
    分级判断期限结构形态的典型程度 - 严格但实用的标准

    分级标准:
    - S级(优秀, ≥95分): 完美单调趋势,方向变化=0次,价差>6%
    - A级(良好, ≥70分): 总体趋势清晰,方向变化≤3次,最多1次显著反转(>1%),价差>5%
    - B级(一般, ≥60分): 有趋势,方向变化≤5次,最多1次显著反转,价差>3%
    - C级(不推荐, <60分): 趋势不明显或有2次以上显著反转

    显著反转定义: 单次反向波动>1%

    Returns:
        str: 等级 (S/A/B/C)
        float: 形态得分(0-100)
        bool: 是否推荐 (只有S/A级推荐)
    """
    if len(contracts) < 6:  # 至少需要6个合约
        return "C", 0, False

    prices = [c['price'] for c in contracts]

    # 1. 计算价格变化幅度
    price_change_pct = abs(prices[-1] - prices[0]) / prices[0] * 100
    if price_change_pct < 2.5:  # 价差小于2.5%,太平坦
        return "C", 0, False

    # 2. 计算单调性 - 严格但合理的标准
    direction_changes = 0
    significant_reversals = 0  # 显著反向波动次数(>1%)
    minor_fluctuations = 0      # 小幅波动次数(0.5-1%)

    for i in range(1, len(prices)):
        price_diff = prices[i] - prices[i-1]
        price_diff_pct = abs(price_diff) / prices[i-1] * 100

        if market_structure == "正向市场":  # Contango应该上涨
            if price_diff < 0:  # 下跌
                direction_changes += 1
                if price_diff_pct > 1.0:  # 下跌超过1%算显著反转
                    significant_reversals += 1
                elif price_diff_pct > 0.5:  # 下跌0.5-1%算小幅波动
                    minor_fluctuations += 1
        elif market_structure == "反向市场":  # Backwardation应该下跌
            if price_diff > 0:  # 上涨
                direction_changes += 1
                if price_diff_pct > 1.0:  # 上涨超过1%算显著反转
                    significant_reversals += 1
                elif price_diff_pct > 0.5:  # 上涨0.5-1%算小幅波动
                    minor_fluctuations += 1

    # 如果有2次以上显著反转,直接判定为C级
    if significant_reversals >= 2:
        return "C", 0, False

    # 3. 计算形态得分(严格但实用的评分标准)
    # 单调性得分(0-70分): 方向变化越少越好,显著反转严重扣分
    if direction_changes == 0:
        monotonicity_score = 70
    elif direction_changes == 1 and significant_reversals == 0:
        monotonicity_score = 65
    elif direction_changes == 2 and significant_reversals == 0:
        monotonicity_score = 60
    elif direction_changes == 3 and significant_reversals == 0:
        monotonicity_score = 55
    elif direction_changes == 3 and significant_reversals == 1:
        # 3次变化但只有1次显著反转，如果总体趋势清晰仍可接受
        monotonicity_score = 50
    elif direction_changes <= 5 and significant_reversals == 0:
        monotonicity_score = 45
    elif direction_changes <= 5 and significant_reversals == 1:
        monotonicity_score = 35
    else:
        monotonicity_score = 0

    # 变化幅度得分(0-30分): 价差越大越好
    amplitude_score = min(30, price_change_pct * 3)

    total_score = monotonicity_score + amplitude_score

    # 分级判断(严格但实用的标准 - 推荐真正有交易价值的品种)
    if total_score >= 95 and direction_changes == 0 and price_change_pct > 6:
        grade = "S"
        recommend = True
    elif total_score >= 70 and direction_changes <= 3 and significant_reversals <= 1 and price_change_pct > 5:
        # A级: 允许少量小波动和最多1次显著反转，但总体趋势必须非常清晰(>5%变化)
        grade = "A"
        recommend = True
    elif total_score >= 60 and direction_changes <= 5 and significant_reversals <= 1 and price_change_pct > 3:
        grade = "B"
        recommend = False
    else:
        grade = "C"
        recommend = False

    return grade, total_score, recommend


def update_all_varieties_data():
    """
    更新所有品种的期限结构数据
    """
    # 中国期货市场所有主要品种
    varieties = {
        # 农产品 - 大商所
        "M": "豆粕",
        "C": "玉米",
        "A": "豆一",
        "B": "豆二",
        "Y": "豆油",
        "P": "棕榈油",
        "CS": "玉米淀粉",
        "JD": "鸡蛋",
        "L": "聚乙烯",
        "V": "聚氯乙烯",
        "PP": "聚丙烯",
        "J": "焦炭",
        "JM": "焦煤",
        "I": "铁矿石",
        "EG": "乙二醇",
        "EB": "苯乙烯",
        "RR": "粳米",
        "LH": "生猪",

        # 农产品 - 郑商所
        "SR": "白糖",
        "CF": "棉花",
        "TA": "PTA",
        "OI": "菜籽油",
        "MA": "甲醇",
        "FG": "玻璃",
        "RM": "菜粕",
        "ZC": "动力煤",
        "SF": "硅铁",
        "SM": "锰硅",
        "UR": "尿素",
        "SA": "纯碱",
        "PF": "短纤",
        "PK": "花生",
        "AP": "苹果",
        "CJ": "红枣",

        # 金属 - 上期所/能源中心
        "CU": "沪铜",
        "AL": "沪铝",
        "ZN": "沪锌",
        "PB": "沪铅",
        "NI": "沪镍",
        "SN": "沪锡",
        "AU": "黄金",
        "AG": "白银",
        "RB": "螺纹钢",
        "HC": "热轧卷板",
        "SS": "不锈钢",
        "FU": "燃料油",
        "BU": "沥青",
        "RU": "橡胶",
        "SP": "纸浆",
        "SC": "原油",
        "LU": "低硫燃料油",
        "NR": "20号胶",

        # 广期所
        "SI": "工业硅",
        "LC": "碳酸锂",

        # 金融 - 中金所
        # "IF": "沪深300",
        # "IC": "中证500",
        # "IH": "上证50",
        # "IM": "中证1000",
        # "TS": "2年期国债",
        # "TF": "5年期国债",
        # "T": "10年期国债",
        # "TL": "30年期国债",
    }

    # 加载缓存数据作为降级方案
    cache_data = load_cache_data()

    all_data = {}  # 所有品种的数据
    recommended_data = {}  # 只有S/A级推荐的品种
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fetcher = FuturesDataFetcher()

    logger.info(f"开始更新期限结构数据: {update_time}")
    logger.info(f"缓存数据: {len(cache_data)}个品种")

    successful_varieties = 0
    recommended_count = 0
    failed_varieties = []

    for code, name in varieties.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"正在获取 {code}({name}) 的合约数据...")

        # 获取2025和2026年的合约
        contracts = get_active_contracts_for_variety(code, years=["25", "26"], fetcher=fetcher)

        if not contracts or len(contracts) == 0:
            logger.warning(f"{code}({name}): 未找到活跃合约,尝试使用缓存")
            # 使用缓存数据
            if code in cache_data and cache_data[code].get('contracts'):
                logger.info(f"{code}({name}): 使用缓存数据 ({len(cache_data[code]['contracts'])}个合约)")
                all_data[code] = cache_data[code]
                all_data[code]['update_time'] = f"{cache_data[code].get('update_time', 'unknown')} (缓存)"
                successful_varieties += 1
            else:
                failed_varieties.append(f"{code}({name})")
            continue

        # 按月份排序
        contracts.sort(key=lambda x: x['month'])

        # 计算期限结构
        prices = [c['price'] for c in contracts]
        if len(prices) >= 2:
            # 判断期限结构:比较第一个和最后一个合约
            if prices[0] < prices[-1]:
                market_structure = "正向市场"  # Contango
                structure_desc = "远期合约价格高于近期合约，市场预期价格上涨"
                trade_suggestion = "做空"
                trade_reason = "Contango结构下，远期合约价格偏高，适合做空远期合约"
            elif prices[0] > prices[-1]:
                market_structure = "反向市场"  # Backwardation
                structure_desc = "近期合约价格高于远期合约，市场预期价格下跌或现货紧张"
                trade_suggestion = "做多"
                trade_reason = "Backwardation结构下，近期合约价格偏高，现货紧张，适合做多"
            else:
                market_structure = "平坦市场"
                structure_desc = "各合约价格基本持平"
                trade_suggestion = "观望"
                trade_reason = "期限结构平坦，暂无明显套利机会"

            # 判断形态是否典型并分级
            grade, structure_score, recommend = classify_term_structure(contracts, market_structure)
        else:
            market_structure = "数据不足"
            structure_desc = ""
            trade_suggestion = "无"
            trade_reason = ""
            grade = "C"
            structure_score = 0
            recommend = False

        # 只保存S/A级品种到推荐列表
        variety_data = {
            "variety_code": code,
            "variety_name": name,
            "market_structure": market_structure,
            "structure_desc": structure_desc,
            "trade_suggestion": trade_suggestion,
            "trade_reason": trade_reason,
            "contracts": contracts,
            "total_contracts": len(contracts),
            "structure_score": round(structure_score, 2),
            "grade": grade,  # S/A/B/C等级
            "recommend": recommend,
            "update_time": update_time
        }

        # 所有品种都保存到all_data
        all_data[code] = variety_data
        successful_varieties += 1

        # 只有推荐的品种(S/A级)保存到recommended_data
        if recommend:
            recommended_data[code] = variety_data
            recommended_count += 1
            logger.info(f"{code}({name}): {market_structure}, {len(contracts)}个合约, 等级:{grade}, 得分:{structure_score:.1f} ⭐")
        else:
            logger.info(f"{code}({name}): {market_structure}, {len(contracts)}个合约, 等级:{grade}, 得分:{structure_score:.1f} (不推荐)")

    # 只有获取到新数据才保存
    if all_data:
        # 保存到JSON文件
        data_dir = Path(__file__).parent.parent / "data"
        data_dir.mkdir(exist_ok=True)

        # 保存所有品种数据
        all_output_file = data_dir / "term_structure_data_all.json"
        with open(all_output_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)

        # 保存推荐品种数据(S/A级)
        recommended_output_file = data_dir / "term_structure_data.json"
        with open(recommended_output_file, 'w', encoding='utf-8') as f:
            json.dump(recommended_data, f, ensure_ascii=False, indent=2)

        logger.info(f"\n{'='*60}")
        logger.info(f"数据更新完成!")
        logger.info(f"所有品种数据保存到: {all_output_file}")
        logger.info(f"推荐品种数据保存到: {recommended_output_file}")
        logger.info(f"成功更新: {successful_varieties}/{len(varieties)} 个品种")
        logger.info(f"推荐品种(S/A级): {recommended_count}个")
        if failed_varieties:
            logger.warning(f"失败品种: {', '.join(failed_varieties)}")

        # 统计Contango和Backwardation数量
        all_contango = sum(1 for v in all_data.values() if v['market_structure'] == '正向市场')
        all_backwardation = sum(1 for v in all_data.values() if v['market_structure'] == '反向市场')
        rec_contango = sum(1 for v in recommended_data.values() if v['market_structure'] == '正向市场')
        rec_backwardation = sum(1 for v in recommended_data.values() if v['market_structure'] == '反向市场')

        logger.info(f"\n所有品种统计:")
        logger.info(f"  Contango结构: {all_contango}个")
        logger.info(f"  Backwardation结构: {all_backwardation}个")
        logger.info(f"\n推荐品种统计:")
        logger.info(f"  Contango结构(S/A级): {rec_contango}个")
        logger.info(f"  Backwardation结构(S/A级): {rec_backwardation}个")
    else:
        logger.error("未获取到任何新数据,保留原有数据文件")

    return all_data, recommended_data


if __name__ == "__main__":
    try:
        data = update_all_varieties_data()
        if data:
            print("\n✅ 数据更新成功!")
        else:
            print("\n⚠️  未获取到新数据,请检查数据源")
    except Exception as e:
        logger.error(f"❌ 数据更新失败: {e}")
        import traceback
        traceback.print_exc()
