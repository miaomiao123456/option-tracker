"""
期限结构数据更新脚本 - 使用优矿API
每天15:05运行,获取当日期货各品种合约的收盘数据

数据源:
1. 优矿API DataAPI.FutuGet - 获取合约信息
2. 优矿API DataAPI.MktFutdGet - 获取日行情数据
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging
import time
from typing import Dict, List, Optional

from app.services.uqer_sdk_client import get_uqer_sdk_client, init_uqer_sdk_client
from config.settings import get_settings
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 品种映射: 品种代码 -> (品种中文名, 合约标的(小写), 交易所代码)
VARIETIES = {
    # 上期所 XSGE
    "CU": ("沪铜", "cu", "XSGE"),
    "AL": ("沪铝", "al", "XSGE"),
    "ZN": ("沪锌", "zn", "XSGE"),
    "PB": ("沪铅", "pb", "XSGE"),
    "NI": ("沪镍", "ni", "XSGE"),
    "SN": ("沪锡", "sn", "XSGE"),
    "AU": ("黄金", "au", "XSGE"),
    "AG": ("白银", "ag", "XSGE"),
    "RB": ("螺纹钢", "rb", "XSGE"),
    "HC": ("热轧卷板", "hc", "XSGE"),
    "SS": ("不锈钢", "ss", "XSGE"),
    "FU": ("燃料油", "fu", "XSGE"),
    "BU": ("沥青", "bu", "XSGE"),
    "RU": ("橡胶", "ru", "XSGE"),
    "SP": ("纸浆", "sp", "XSGE"),
    "SC": ("原油", "sc", "XSGE"),
    "LU": ("低硫燃料油", "lu", "XSGE"),
    "NR": ("20号胶", "nr", "XSGE"),

    # 大商所 XDCE
    "M": ("豆粕", "m", "XDCE"),
    "C": ("玉米", "c", "XDCE"),
    "A": ("豆一", "a", "XDCE"),
    "B": ("豆二", "b", "XDCE"),
    "Y": ("豆油", "y", "XDCE"),
    "P": ("棕榈油", "p", "XDCE"),
    "CS": ("玉米淀粉", "cs", "XDCE"),
    "JD": ("鸡蛋", "jd", "XDCE"),
    "L": ("聚乙烯", "l", "XDCE"),
    "V": ("聚氯乙烯", "v", "XDCE"),
    "PP": ("聚丙烯", "pp", "XDCE"),
    "J": ("焦炭", "j", "XDCE"),
    "JM": ("焦煤", "jm", "XDCE"),
    "I": ("铁矿石", "i", "XDCE"),
    "EG": ("乙二醇", "eg", "XDCE"),
    "EB": ("苯乙烯", "eb", "XDCE"),
    "RR": ("粳米", "rr", "XDCE"),
    "LH": ("生猪", "lh", "XDCE"),

    # 郑商所 XZCE
    "SR": ("白糖", "SR", "XZCE"),
    "CF": ("棉花", "CF", "XZCE"),
    "TA": ("PTA", "TA", "XZCE"),
    "OI": ("菜籽油", "OI", "XZCE"),
    "MA": ("甲醇", "MA", "XZCE"),
    "FG": ("玻璃", "FG", "XZCE"),
    "RM": ("菜粕", "RM", "XZCE"),
    "ZC": ("动力煤", "ZC", "XZCE"),
    "SF": ("硅铁", "SF", "XZCE"),
    "SM": ("锰硅", "SM", "XZCE"),
    "UR": ("尿素", "UR", "XZCE"),
    "SA": ("纯碱", "SA", "XZCE"),
    "PF": ("短纤", "PF", "XZCE"),
    "PK": ("花生", "PK", "XZCE"),
    "AP": ("苹果", "AP", "XZCE"),
    "CJ": ("红枣", "CJ", "XZCE"),
}


class TermStructureUpdaterUqer:
    """期限结构数据更新器 - 使用优矿SDK"""

    def __init__(self):
        self.uqer_client = get_uqer_sdk_client()

        if not self.uqer_client:
            # 尝试从配置初始化
            settings = get_settings()
            if settings.UQER_TOKEN:
                self.uqer_client = init_uqer_sdk_client(settings.UQER_TOKEN)
            else:
                raise ValueError("优矿Token未配置")

    def get_active_contracts_for_variety(
        self,
        variety_code: str,
        variety_name: str,
        contract_object: str,
        exchange_cd: str
    ) -> List[Dict]:
        """
        获取指定品种的活跃合约数据

        Args:
            variety_code: 品种代码(大写),如 "CU"
            variety_name: 品种中文名,如 "沪铜"
            contract_object: 合约标的(优矿格式),如 "cu"
            exchange_cd: 交易所代码,如 "XSGE"

        Returns:
            合约列表
        """
        try:
            # 获取最近的交易日期
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5)  # 取最近5天数据

            # 直接获取该品种所有合约的行情数据
            logger.info(f"获取 {variety_code}({variety_name}) 的行情数据...")
            market_data = self.uqer_client.get_futures_daily(
                begin_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                exchange_cd=exchange_cd
            )

            if market_data is None or market_data.empty:
                logger.warning(f"{variety_code}: 未获取到行情数据")
                return []

            # 过滤出该品种的数据 (按contractObject字段过滤)
            if 'contractObject' in market_data.columns:
                market_data = market_data[market_data['contractObject'].str.lower() == contract_object.lower()]

            if market_data.empty:
                logger.warning(f"{variety_code}: 无该品种行情数据")
                return []

            # 按交易日期取最新
            market_data['tradeDate'] = pd.to_datetime(market_data['tradeDate'])
            latest_date = market_data['tradeDate'].max()
            latest_data = market_data[market_data['tradeDate'] == latest_date]

            # 提取合约代码中的月份
            import re
            contracts = []

            for _, row in latest_data.iterrows():
                ticker = str(row.get('ticker', ''))

                # 提取品种代码和月份
                # 格式1: cu2501 (XSGE/XDCE) -> cu, 2501
                # 格式2: SR601 (XZCE) -> SR, 601
                match = re.match(r'([a-zA-Z]+)(\d{3,4})', ticker, re.IGNORECASE)
                if not match:
                    continue

                contract_prefix = match.group(1)
                month_code = match.group(2)

                # 检查是否匹配当前品种 (忽略大小写)
                if contract_prefix.lower() != contract_object.lower():
                    continue

                # 统一月份代码格式为YYMM
                if len(month_code) == 3:
                    # XZCE格式: 601 -> 2601
                    month_code = '2' + month_code
                elif len(month_code) == 4:
                    # XSGE/XDCE格式: 2501 -> 2501
                    pass

                # 提取价格和持仓信息
                close_price = row.get('closePrice', 0)
                settle_price = row.get('settlPrice', 0)
                price = settle_price if settle_price > 0 else close_price

                volume = int(row.get('turnoverVol', 0))
                open_interest = int(row.get('openInt', 0))

                # 跳过价格无效的合约 (价格<=0 或 nan)
                if not price or price <= 0 or pd.isna(price):
                    continue

                contracts.append({
                    "symbol": ticker.upper(),
                    "month": month_code,
                    "price": float(price),
                    "volume": volume,
                    "open_interest": open_interest,
                    "date": row['tradeDate'].strftime("%Y-%m-%d"),
                    "source": "uqer"
                })

                logger.info(f"✓ {ticker}: 价格={price}, 持仓={open_interest}, 成交量={volume}")

            # 按月份排序
            contracts.sort(key=lambda x: x['month'])

            logger.info(f"{variety_code}: 成功获取{len(contracts)}个合约")
            return contracts

        except Exception as e:
            logger.error(f"获取{variety_code}合约数据失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def classify_term_structure(self, contracts: List[Dict], market_structure: str):
        """
        分级判断期限结构形态的典型程度

        Returns:
            tuple: (等级, 得分, 是否推荐)
        """
        if len(contracts) < 6:
            return "C", 0, False

        prices = [c['price'] for c in contracts]

        # 1. 价格变化幅度
        price_change_pct = abs(prices[-1] - prices[0]) / prices[0] * 100
        if price_change_pct < 2.5:
            return "C", 0, False

        # 2. 计算单调性
        direction_changes = 0
        significant_reversals = 0

        for i in range(1, len(prices)):
            price_diff = prices[i] - prices[i-1]
            price_diff_pct = abs(price_diff) / prices[i-1] * 100

            if market_structure == "正向市场":
                if price_diff < 0:
                    direction_changes += 1
                    if price_diff_pct > 1.0:
                        significant_reversals += 1
            elif market_structure == "反向市场":
                if price_diff > 0:
                    direction_changes += 1
                    if price_diff_pct > 1.0:
                        significant_reversals += 1

        if significant_reversals >= 2:
            return "C", 0, False

        # 3. 计算得分
        if direction_changes == 0:
            monotonicity_score = 70
        elif direction_changes <= 3 and significant_reversals == 0:
            monotonicity_score = 60
        elif direction_changes <= 5 and significant_reversals <= 1:
            monotonicity_score = 45
        else:
            monotonicity_score = 0

        amplitude_score = min(30, price_change_pct * 3)
        total_score = monotonicity_score + amplitude_score

        # 4. 分级
        if total_score >= 95 and direction_changes == 0 and price_change_pct > 6:
            return "S", total_score, True
        elif total_score >= 70 and direction_changes <= 3 and significant_reversals <= 1 and price_change_pct > 5:
            return "A", total_score, True
        elif total_score >= 60:
            return "B", total_score, False
        else:
            return "C", total_score, False

    def update_all_varieties(self):
        """更新所有品种的期限结构数据"""
        all_data = {}
        recommended_data = {}
        update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        logger.info(f"开始更新期限结构数据: {update_time}")

        successful_varieties = 0
        recommended_count = 0
        failed_varieties = []

        for code, (name, contract_obj, exchange) in VARIETIES.items():
            logger.info(f"\n{'='*60}")
            logger.info(f"正在获取 {code}({name}) 的合约数据...")

            contracts = self.get_active_contracts_for_variety(
                code, name, contract_obj, exchange
            )

            if not contracts or len(contracts) == 0:
                logger.warning(f"{code}({name}): 未找到活跃合约")
                failed_varieties.append(f"{code}({name})")
                continue

            # 计算期限结构
            prices = [c['price'] for c in contracts]
            if len(prices) >= 2:
                if prices[0] < prices[-1]:
                    market_structure = "正向市场"
                    structure_desc = "远期合约价格高于近期合约，市场预期价格上涨"
                    trade_suggestion = "做空"
                    trade_reason = "Contango结构下，远期合约价格偏高，适合做空远期合约"
                elif prices[0] > prices[-1]:
                    market_structure = "反向市场"
                    structure_desc = "近期合约价格高于远期合约，市场预期价格下跌或现货紧张"
                    trade_suggestion = "做多"
                    trade_reason = "Backwardation结构下，近期合约价格偏高，现货紧张，适合做多"
                else:
                    market_structure = "平坦市场"
                    structure_desc = "各合约价格基本持平"
                    trade_suggestion = "观望"
                    trade_reason = "期限结构平坦，暂无明显套利机会"

                grade, structure_score, recommend = self.classify_term_structure(
                    contracts, market_structure
                )
            else:
                market_structure = "数据不足"
                structure_desc = ""
                trade_suggestion = "无"
                trade_reason = ""
                grade = "C"
                structure_score = 0
                recommend = False

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
                "grade": grade,
                "recommend": recommend,
                "update_time": update_time
            }

            all_data[code] = variety_data
            successful_varieties += 1

            if recommend:
                recommended_data[code] = variety_data
                recommended_count += 1
                logger.info(f"{code}({name}): {market_structure}, 等级:{grade}, 得分:{structure_score:.1f} ⭐")
            else:
                logger.info(f"{code}({name}): {market_structure}, 等级:{grade}, 得分:{structure_score:.1f}")

            time.sleep(0.2)  # 避免请求过快

        # 保存数据
        if all_data:
            data_dir = Path(__file__).parent.parent / "data"
            data_dir.mkdir(exist_ok=True)

            # 保存所有品种
            all_output_file = data_dir / "term_structure_data_all.json"
            with open(all_output_file, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)

            # 保存推荐品种
            recommended_output_file = data_dir / "term_structure_data.json"
            with open(recommended_output_file, 'w', encoding='utf-8') as f:
                json.dump(recommended_data, f, ensure_ascii=False, indent=2)

            logger.info(f"\n{'='*60}")
            logger.info(f"数据更新完成!")
            logger.info(f"成功更新: {successful_varieties}/{len(VARIETIES)} 个品种")
            logger.info(f"推荐品种(S/A级): {recommended_count}个")
            if failed_varieties:
                logger.warning(f"失败品种: {', '.join(failed_varieties)}")

        return all_data, recommended_data


if __name__ == "__main__":
    try:
        import pandas as pd  # 需要导入pandas
        updater = TermStructureUpdaterUqer()
        data = updater.update_all_varieties()
        if data:
            print("\n✅ 数据更新成功!")
    except Exception as e:
        logger.error(f"❌ 数据更新失败: {e}")
        import traceback
        traceback.print_exc()
