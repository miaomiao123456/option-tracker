"""
优矿资金面数据爬虫
使用优矿API获取期货多空持仓数据

数据源:
- DataAPI.MktFutOiRatioGet: 品种级别的多空总持仓
- DataAPI.MktFutMLRGet: 期货会员多头持仓排名
- DataAPI.MktFutMSRGet: 期货会员空头持仓排名
- DataAPI.MktFutMTRGet: 期货龙虎榜Top

数据类型: 品种级别的多空总持仓 + 详细席位排名数据
"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
from app.services.uqer_sdk_client import get_uqer_sdk_client
from app.models.database import SessionLocal
from app.models.models import InstitutionalPosition, Commodity

logger = logging.getLogger(__name__)


class CapitalSpiderUqer:
    """优矿资金面数据爬虫"""

    # 交易所代码映射
    EXCHANGE_MAP = {
        'SHFE': 'XSGE',  # 上期所
        'DCE': 'XDCE',   # 大商所
        'CZCE': 'XZCE',  # 郑商所
        'CFFEX': 'CCFX', # 中金所
    }

    # 品种代码映射 (小写 -> 大写)
    VARIETY_MAP = {
        'cu': 'CU', 'al': 'AL', 'zn': 'ZN', 'pb': 'PB', 'ni': 'NI',
        'sn': 'SN', 'au': 'AU', 'ag': 'AG', 'rb': 'RB', 'hc': 'HC',
        'ru': 'RU', 'bu': 'BU', 'fu': 'FU', 'sc': 'SC',
        'a': 'A', 'b': 'B', 'c': 'C', 'm': 'M', 'y': 'Y',
        'p': 'P', 'i': 'I', 'j': 'J', 'jm': 'JM', 'v': 'V',
        'l': 'L', 'pp': 'PP', 'eg': 'EG', 'eb': 'EB',
        'ta': 'TA', 'ma': 'MA', 'fg': 'FG', 'cf': 'CF', 'sr': 'SR',
        'rm': 'RM', 'oi': 'OI', 'zc': 'ZC', 'sm': 'SM', 'sf': 'SF',
        'sa': 'SA', 'ur': 'UR', 'pk': 'PK', 'ap': 'AP',
        'if': 'IF', 'ic': 'IC', 'ih': 'IH', 'im': 'IM',
    }

    def __init__(self):
        self.client = get_uqer_sdk_client()
        if not self.client:
            raise ValueError("优矿SDK客户端未初始化,请先调用 init_uqer_sdk_client()")

    def get_exchange_code(self, variety_code: str) -> Optional[str]:
        """
        根据品种代码获取交易所代码

        Args:
            variety_code: 品种代码 (大小写均可), 如 'cu', 'CU', 'rb', 'RB'

        Returns:
            优矿交易所代码 (XSGE/XDCE/XZCE/CCFX) 或 None
        """
        db = SessionLocal()
        try:
            # 尝试大小写查询
            commodity = db.query(Commodity).filter(
                Commodity.code == variety_code.upper()
            ).first()

            if not commodity:
                # 再尝试小写
                commodity = db.query(Commodity).filter(
                    Commodity.code == variety_code.lower()
                ).first()

            if not commodity or not commodity.exchange:
                logger.warning(f"未找到品种 {variety_code} 的交易所信息")
                return None

            return self.EXCHANGE_MAP.get(commodity.exchange)

        finally:
            db.close()

    def fetch_variety_positions(
        self,
        variety_code: str,
        target_date: Optional[date] = None,
        top_n: int = 20
    ) -> Optional[List[Dict]]:
        """
        获取指定品种的多空持仓数据 (使用MktFutOiRatioGet API)

        注: 由于MktFutMLRGet等席位排名API需要专业版权限,
        这里使用MktFutOiRatioGet获取品种级别的多空总持仓数据

        Args:
            variety_code: 品种代码 (小写), 如 'cu', 'rb'
            target_date: 目标日期,默认为当天
            top_n: 保留参数(兼容性),实际不使用

        Returns:
            持仓数据列表 [{'broker_name', 'net_position', 'position_change', 'win_rate', 'record_date'}]
            注: 由于是品种级总持仓,broker_name统一为'市场总持仓'
        """
        if target_date is None:
            target_date = date.today()

        try:
            # 转换品种代码为大写
            contract_object = self.VARIETY_MAP.get(variety_code.lower())
            if not contract_object:
                logger.warning(f"不支持的品种代码: {variety_code}")
                return None

            # 格式化日期
            trade_date = target_date.strftime('%Y%m%d')
            # 获取前一天的数据用于计算变化
            prev_date = (target_date - timedelta(days=3)).strftime('%Y%m%d')

            logger.info(f"开始获取 {variety_code}({contract_object}) 的多空持仓数据...")

            # 获取多空持仓比例数据
            df = self.client.get_oi_ratio(
                contract_object=contract_object,
                begin_date=prev_date,
                end_date=trade_date
            )

            if df is None or df.empty:
                logger.warning(f"未获取到 {variety_code} 的持仓数据")
                return None

            # 获取最新一条数据
            latest = df.iloc[-1]
            long_oi = int(latest.get('longOpenInt', 0))
            short_oi = int(latest.get('shortOpenInt', 0))
            net_position = long_oi - short_oi

            # 计算变化(如果有历史数据)
            position_change = 0
            if len(df) >= 2:
                prev = df.iloc[-2]
                prev_long = int(prev.get('longOpenInt', 0))
                prev_short = int(prev.get('shortOpenInt', 0))
                prev_net = prev_long - prev_short
                position_change = net_position - prev_net

            # 转换为目标格式
            positions = [{
                'broker_name': f'市场总持仓(多:{long_oi}|空:{short_oi})',
                'net_position': net_position,
                'position_change': position_change,
                'win_rate': None,  # 该API不提供胜率
                'record_date': target_date
            }]

            logger.info(f"✅ 成功获取 {variety_code} 的持仓数据: 净持仓={net_position}, 变化={position_change}")
            return positions

        except Exception as e:
            logger.error(f"获取持仓数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def fetch_broker_positions(
        self,
        variety_code: str,
        target_date: Optional[date] = None,
        top_n: int = 20
    ) -> Optional[List[Dict]]:
        """
        获取指定品种的详细席位排名数据 (使用MktFutMLRGet和MktFutMSRGet API)

        Args:
            variety_code: 品种代码 (小写), 如 'cu', 'rb'
            target_date: 目标日期,默认为当天
            top_n: 返回前N名席位

        Returns:
            持仓数据列表 [{'broker_name', 'net_position', 'position_change', 'win_rate', 'record_date'}]
        """
        if target_date is None:
            target_date = date.today()

        try:
            # 转换品种代码为大写
            contract_object = self.VARIETY_MAP.get(variety_code.lower())
            if not contract_object:
                logger.warning(f"不支持的品种代码: {variety_code}")
                return None

            # 获取交易所代码
            exchange_cd = self.get_exchange_code(variety_code)

            # 格式化日期
            trade_date = target_date.strftime('%Y%m%d')
            # 获取前一天的数据用于计算变化
            prev_date = (target_date - timedelta(days=1)).strftime('%Y%m%d')

            logger.info(f"开始获取 {variety_code}({contract_object}) 的详细席位排名数据...")

            positions = []

            # 获取多头持仓排名
            long_df = self.client.get_futures_long_rank(
                contract_object=contract_object,
                exchange_cd=exchange_cd,
                trade_date=trade_date
            )

            # 获取前一天的多头数据用于计算变化
            long_prev_df = self.client.get_futures_long_rank(
                contract_object=contract_object,
                exchange_cd=exchange_cd,
                trade_date=prev_date
            )

            # 获取空头持仓排名
            short_df = self.client.get_futures_short_rank(
                contract_object=contract_object,
                exchange_cd=exchange_cd,
                trade_date=trade_date
            )

            # 获取前一天的空头数据用于计算变化
            short_prev_df = self.client.get_futures_short_rank(
                contract_object=contract_object,
                exchange_cd=exchange_cd,
                trade_date=prev_date
            )

            # 建立前一天数据的字典便于查询
            prev_long_dict = {}
            prev_short_dict = {}
            if long_prev_df is not None and not long_prev_df.empty:
                for _, row in long_prev_df.iterrows():
                    broker = row.get('partyFullName', row.get('memberAbbr', ''))
                    prev_long_dict[broker] = int(row.get('longPosition', row.get('longOpenInt', 0)))
            if short_prev_df is not None and not short_prev_df.empty:
                for _, row in short_prev_df.iterrows():
                    broker = row.get('partyFullName', row.get('memberAbbr', ''))
                    prev_short_dict[broker] = int(row.get('shortPosition', row.get('shortOpenInt', 0)))

            # 处理多头排名数据
            broker_data = {}  # {broker_name: {'long': x, 'short': y, 'long_change': a, 'short_change': b}}

            if long_df is not None and not long_df.empty:
                logger.info(f"获取到 {len(long_df)} 条多头排名数据")
                for _, row in long_df.head(top_n).iterrows():
                    broker = row.get('partyFullName', row.get('memberAbbr', ''))
                    long_pos = int(row.get('longPosition', row.get('longOpenInt', 0)))
                    prev_long = prev_long_dict.get(broker, 0)
                    long_change = long_pos - prev_long

                    if broker not in broker_data:
                        broker_data[broker] = {'long': 0, 'short': 0, 'long_change': 0, 'short_change': 0}
                    broker_data[broker]['long'] = long_pos
                    broker_data[broker]['long_change'] = long_change
            else:
                logger.warning(f"未获取到 {variety_code} 的多头排名数据")

            # 处理空头排名数据
            if short_df is not None and not short_df.empty:
                logger.info(f"获取到 {len(short_df)} 条空头排名数据")
                for _, row in short_df.head(top_n).iterrows():
                    broker = row.get('partyFullName', row.get('memberAbbr', ''))
                    short_pos = int(row.get('shortPosition', row.get('shortOpenInt', 0)))
                    prev_short = prev_short_dict.get(broker, 0)
                    short_change = short_pos - prev_short

                    if broker not in broker_data:
                        broker_data[broker] = {'long': 0, 'short': 0, 'long_change': 0, 'short_change': 0}
                    broker_data[broker]['short'] = short_pos
                    broker_data[broker]['short_change'] = short_change
            else:
                logger.warning(f"未获取到 {variety_code} 的空头排名数据")

            # 计算净持仓并生成结果
            for broker, data in broker_data.items():
                net_position = data['long'] - data['short']
                position_change = data['long_change'] - data['short_change']

                positions.append({
                    'broker_name': broker,
                    'net_position': net_position,
                    'position_change': position_change,
                    'long_position': data['long'],
                    'short_position': data['short'],
                    'win_rate': None,  # API不提供胜率
                    'record_date': target_date
                })

            if positions:
                # 按净持仓绝对值排序
                positions.sort(key=lambda x: abs(x['net_position']), reverse=True)
                logger.info(f"✅ 成功获取 {variety_code} 的 {len(positions)} 条席位数据")
            else:
                logger.warning(f"未能获取 {variety_code} 的席位排名数据")

            return positions if positions else None

        except Exception as e:
            logger.error(f"获取席位排名数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def fetch_all_broker_positions(
        self,
        target_date: Optional[date] = None,
        top_n: int = 20
    ) -> Dict[str, List[Dict]]:
        """
        获取所有品种的详细席位排名数据

        Args:
            target_date: 目标日期,默认为当天
            top_n: 每个品种返回前N名席位

        Returns:
            {variety_code: [positions]}
        """
        if target_date is None:
            target_date = date.today()

        db = SessionLocal()
        try:
            # 获取所有品种列表
            commodities = db.query(Commodity).all()

            all_positions = {}
            success_count = 0
            fail_count = 0

            for commodity in commodities:
                variety_code = commodity.code
                logger.info(f"正在获取 {variety_code}({commodity.name}) 的详细席位数据...")

                positions = self.fetch_broker_positions(
                    variety_code=variety_code,
                    target_date=target_date,
                    top_n=top_n
                )

                if positions:
                    all_positions[variety_code] = positions
                    success_count += 1
                else:
                    fail_count += 1

                # 避免频繁请求
                import time
                time.sleep(0.3)

            logger.info(f"✅ 完成所有品种席位数据获取: 成功 {success_count}, 失败 {fail_count}")
            return all_positions

        finally:
            db.close()

    def save_broker_positions_to_db(
        self,
        variety_code: str,
        positions: List[Dict]
    ) -> int:
        """
        保存详细席位持仓数据到数据库

        Args:
            variety_code: 品种代码
            positions: 席位持仓列表

        Returns:
            保存的记录数
        """
        db = SessionLocal()
        saved_count = 0
        try:
            for pos in positions:
                # 检查是否已存在
                existing = db.query(InstitutionalPosition).filter(
                    InstitutionalPosition.comm_code == variety_code.upper(),
                    InstitutionalPosition.broker_name == pos['broker_name'],
                    InstitutionalPosition.record_date == pos['record_date']
                ).first()

                if existing:
                    # 更新现有记录
                    existing.net_position = pos['net_position']
                    existing.position_change = pos['position_change']
                    existing.win_rate = pos['win_rate']
                else:
                    # 创建新记录
                    record = InstitutionalPosition(
                        comm_code=variety_code.upper(),
                        broker_name=pos['broker_name'],
                        net_position=pos['net_position'],
                        position_change=pos['position_change'],
                        win_rate=pos['win_rate'],
                        record_date=pos['record_date']
                    )
                    db.add(record)
                    saved_count += 1

            db.commit()
            logger.info(f"✅ 成功保存 {variety_code} 的 {saved_count} 条席位数据到数据库")
            return saved_count

        except Exception as e:
            db.rollback()
            logger.error(f"保存数据到数据库失败: {e}")
            return 0

        finally:
            db.close()

    def update_all_broker_positions(
        self,
        target_date: Optional[date] = None,
        top_n: int = 20
    ) -> Dict:
        """
        更新所有品种的详细席位持仓数据到数据库

        Args:
            target_date: 目标日期,默认为当天
            top_n: 每个品种返回前N名席位

        Returns:
            统计信息 {'success_count', 'fail_count', 'total_records'}
        """
        if target_date is None:
            target_date = date.today()

        logger.info(f"=" * 60)
        logger.info(f"开始更新所有品种的详细席位持仓数据 - 日期: {target_date}")
        logger.info(f"=" * 60)

        # 获取所有品种的席位数据
        all_positions = self.fetch_all_broker_positions(target_date, top_n)

        # 保存到数据库
        success_count = 0
        fail_count = 0
        total_records = 0

        for variety_code, positions in all_positions.items():
            saved = self.save_broker_positions_to_db(variety_code, positions)
            if saved > 0:
                success_count += 1
                total_records += saved
            else:
                fail_count += 1

        logger.info(f"=" * 60)
        logger.info(f"详细席位数据更新完成:")
        logger.info(f"  成功品种数: {success_count}")
        logger.info(f"  失败品种数: {fail_count}")
        logger.info(f"  总记录数: {total_records}")
        logger.info(f"=" * 60)

        return {
            'success_count': success_count,
            'fail_count': fail_count,
            'total_records': total_records,
            'date': target_date
        }

    def fetch_all_varieties_positions(
        self,
        target_date: Optional[date] = None,
        top_n: int = 20
    ) -> Dict[str, List[Dict]]:
        """
        获取所有品种的席位持仓数据

        Args:
            target_date: 目标日期,默认为当天
            top_n: 每个品种返回前N名席位

        Returns:
            {variety_code: [positions]}
        """
        if target_date is None:
            target_date = date.today()

        db = SessionLocal()
        try:
            # 获取所有品种列表
            commodities = db.query(Commodity).all()

            all_positions = {}
            success_count = 0
            fail_count = 0

            for commodity in commodities:
                variety_code = commodity.code
                logger.info(f"正在获取 {variety_code}({commodity.name}) 的席位数据...")

                positions = self.fetch_variety_positions(
                    variety_code=variety_code,
                    target_date=target_date,
                    top_n=top_n
                )

                if positions:
                    all_positions[variety_code] = positions
                    success_count += 1
                else:
                    fail_count += 1

                # 避免频繁请求
                import time
                time.sleep(0.5)

            logger.info(f"✅ 完成所有品种席位数据获取: 成功 {success_count}, 失败 {fail_count}")
            return all_positions

        finally:
            db.close()

    def save_positions_to_db(
        self,
        variety_code: str,
        positions: List[Dict]
    ) -> bool:
        """
        保存席位持仓数据到数据库

        Args:
            variety_code: 品种代码
            positions: 席位持仓列表

        Returns:
            是否保存成功
        """
        db = SessionLocal()
        try:
            for pos in positions:
                # 检查是否已存在
                existing = db.query(InstitutionalPosition).filter(
                    InstitutionalPosition.comm_code == variety_code,
                    InstitutionalPosition.broker_name == pos['broker_name'],
                    InstitutionalPosition.record_date == pos['record_date']
                ).first()

                if existing:
                    # 更新现有记录
                    existing.net_position = pos['net_position']
                    existing.position_change = pos['position_change']
                    existing.win_rate = pos['win_rate']
                else:
                    # 创建新记录
                    record = InstitutionalPosition(
                        comm_code=variety_code,
                        broker_name=pos['broker_name'],
                        net_position=pos['net_position'],
                        position_change=pos['position_change'],
                        win_rate=pos['win_rate'],
                        record_date=pos['record_date']
                    )
                    db.add(record)

            db.commit()
            logger.info(f"✅ 成功保存 {len(positions)} 条席位数据到数据库")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"保存数据到数据库失败: {e}")
            return False

        finally:
            db.close()

    def update_all_positions(
        self,
        target_date: Optional[date] = None,
        top_n: int = 20
    ) -> Dict:
        """
        更新所有品种的席位持仓数据到数据库

        Args:
            target_date: 目标日期,默认为当天
            top_n: 每个品种返回前N名席位

        Returns:
            统计信息 {'success_count', 'fail_count', 'total_records'}
        """
        if target_date is None:
            target_date = date.today()

        logger.info(f"=" * 60)
        logger.info(f"开始更新所有品种的席位持仓数据 - 日期: {target_date}")
        logger.info(f"=" * 60)

        # 获取所有品种的席位数据
        all_positions = self.fetch_all_varieties_positions(target_date, top_n)

        # 保存到数据库
        success_count = 0
        fail_count = 0
        total_records = 0

        for variety_code, positions in all_positions.items():
            if self.save_positions_to_db(variety_code, positions):
                success_count += 1
                total_records += len(positions)
            else:
                fail_count += 1

        logger.info(f"=" * 60)
        logger.info(f"席位数据更新完成:")
        logger.info(f"  成功品种数: {success_count}")
        logger.info(f"  失败品种数: {fail_count}")
        logger.info(f"  总记录数: {total_records}")
        logger.info(f"=" * 60)

        return {
            'success_count': success_count,
            'fail_count': fail_count,
            'total_records': total_records,
            'date': target_date
        }


# 测试代码
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    from app.services.uqer_sdk_client import init_uqer_sdk_client
    from config.settings import get_settings

    settings = get_settings()

    # 初始化优矿客户端
    init_uqer_sdk_client(settings.UQER_TOKEN)

    # 创建爬虫实例
    spider = CapitalSpiderUqer()

    # 测试获取单个品种席位数据
    print("=== 测试获取铜(cu)的席位数据 ===")
    positions = spider.fetch_variety_positions('cu', top_n=10)
    if positions:
        print(f"获取到 {len(positions)} 条席位数据")
        for pos in positions[:3]:
            print(f"  {pos['broker_name']}: 净持仓={pos['net_position']}, 变化={pos['position_change']}")

    # 测试保存到数据库
    if positions:
        print("\n=== 测试保存到数据库 ===")
        spider.save_positions_to_db('cu', positions)

    # 测试更新所有品种 (可选,注释掉以避免大量请求)
    # print("\n=== 测试更新所有品种 ===")
    # result = spider.update_all_positions(top_n=10)
    # print(f"统计: {result}")
