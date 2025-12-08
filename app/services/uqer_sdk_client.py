"""
优矿(uqer) SDK 客户端封装
用于访问优矿平台的期货数据
"""
import os
import pandas as pd
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date

logger = logging.getLogger(__name__)


class UqerSDKClient:
    """优矿SDK客户端封装"""

    def __init__(self, token: str = None):
        """
        初始化优矿SDK客户端
        Args:
            token: 优矿API Token (如果不提供，会从环境变量读取)
        """
        # 设置token到环境变量
        if token:
            os.environ['access_token'] = token
            self.token = token
        else:
            self.token = os.environ.get('access_token', '')

        if not self.token:
            logger.warning("未设置优矿Token，API调用可能失败")

        # 延迟导入DataAPI，确保token已设置
        from uqer import DataAPI
        self.DataAPI = DataAPI

    def get_futures_contracts(
        self,
        ticker: Optional[str] = None,
        exchange_cd: str = "XSGE",
        contract_status: Optional[str] = None,
        contract_object: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        获取期货合约基本信息 (DataAPI.FutuGet)

        Args:
            ticker: 合约交易代码,如 "cu2506"
            exchange_cd: 交易所代码 XSGE(上期所)/XDCE(大商所)/XZCE(郑商所)/CCFX(中金所)
            contract_status: 合约状态 (可选)
            contract_object: 合约标的,如 "cu"(铜)

        Returns:
            包含合约信息的DataFrame
        """
        try:
            params = {
                'exchangeCD': exchange_cd,
                'pandas': '1'
            }

            if ticker:
                params['ticker'] = ticker
            if contract_object:
                params['contractObject'] = contract_object
            if contract_status:
                params['contractStatus'] = contract_status

            df = self.DataAPI.FutuGet(**params)
            return df if not df.empty else None

        except Exception as e:
            logger.error(f"获取合约信息失败: {e}")
            return None

    def get_futures_daily(
        self,
        ticker: Optional[str] = None,
        trade_date: Optional[str] = None,
        begin_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange_cd: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        获取期货日行情数据 (DataAPI.MktFutdGet)

        Args:
            ticker: 合约代码,如 "cu2501"
            trade_date: 交易日期 YYYYMMDD
            begin_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            exchange_cd: 交易所代码

        Returns:
            包含日行情的DataFrame
        """
        try:
            params = {'pandas': '1'}

            if ticker:
                params['ticker'] = ticker
            if trade_date:
                params['tradeDate'] = trade_date
            if begin_date:
                params['beginDate'] = begin_date
            if end_date:
                params['endDate'] = end_date
            if exchange_cd:
                params['exchangeCD'] = exchange_cd

            df = self.DataAPI.MktFutdGet(**params)
            return df if not df.empty else None

        except Exception as e:
            logger.error(f"获取日行情失败: {e}")
            return None

    def get_warehouse_receipt(
        self,
        contract_object: Optional[str] = None,
        exchange_cd: Optional[str] = None,
        begin_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        获取期货仓单日报 (DataAPI.MktFutWRdGet)

        Args:
            contract_object: 品种代码,如 "CU", "AU" (大写)
            exchange_cd: 交易所代码
            begin_date: 查询起始日期 YYYYMMDD
            end_date: 查询截止日期 YYYYMMDD

        Returns:
            包含仓单信息的DataFrame
        """
        try:
            params = {'pandas': '1'}

            if contract_object:
                params['contractObject'] = contract_object
            if exchange_cd:
                params['exchangeCD'] = exchange_cd
            if begin_date:
                params['beginDate'] = begin_date
            if end_date:
                params['endDate'] = end_date

            df = self.DataAPI.MktFutWRdGet(**params)
            return df if not df.empty else None

        except Exception as e:
            logger.error(f"获取仓单数据失败: {e}")
            return None

    def get_main_contract_daily(
        self,
        contract_object: str,
        trade_date: Optional[str] = None,
        begin_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange_cd: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        获取主力合约日行情

        通过获取某个标的所有合约,按持仓量筛选出主力合约

        Args:
            contract_object: 合约标的,如 "cu"
            trade_date: 交易日期 YYYYMMDD
            begin_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            exchange_cd: 交易所代码

        Returns:
            主力合约的日行情数据
        """
        try:
            # 获取所有合约的行情
            df = self.get_futures_daily(
                trade_date=trade_date,
                begin_date=begin_date,
                end_date=end_date,
                exchange_cd=exchange_cd
            )

            if df is None or df.empty:
                return None

            # 过滤出指定品种
            df_filtered = df[df['contractObject'].str.lower() == contract_object.lower()]

            if df_filtered.empty:
                return None

            # 按日期分组,取持仓量最大的合约作为主力合约
            if 'openInt' in df_filtered.columns and 'tradeDate' in df_filtered.columns:
                main_contracts = df_filtered.loc[
                    df_filtered.groupby('tradeDate')['openInt'].idxmax()
                ]
                return main_contracts

            return df_filtered

        except Exception as e:
            logger.error(f"获取主力合约数据失败: {e}")
            return None


# 创建一个全局客户端实例(需要在使用前初始化)
_uqer_sdk_client: Optional[UqerSDKClient] = None


def init_uqer_sdk_client(token: str) -> UqerSDKClient:
    """
    初始化全局优矿SDK客户端
    Args:
        token: 优矿API Token
    Returns:
        UqerSDKClient实例
    """
    global _uqer_sdk_client
    _uqer_sdk_client = UqerSDKClient(token)
    return _uqer_sdk_client


def get_uqer_sdk_client() -> Optional[UqerSDKClient]:
    """
    获取全局优矿SDK客户端实例
    Returns:
        UqerSDKClient实例或None
    """
    return _uqer_sdk_client


# 测试代码
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 配置token
    token = "190bbd239ab55cb2f3f2919601622b0b793e94c35d7967e0c4b325682eddd981"
    client = UqerSDKClient(token)

    # 测试获取合约信息
    print("=== 测试获取铜合约信息 ===")
    contracts = client.get_futures_contracts(contract_object="cu", exchange_cd="XSGE")
    if contracts is not None:
        print(f"✅ 获取到 {len(contracts)} 个合约")
        print(contracts.head(3))

    # 测试获取仓单数据
    print("\n=== 测试获取铜仓单数据 ===")
    from datetime import datetime, timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    warehouse = client.get_warehouse_receipt(
        contract_object="CU",
        exchange_cd="XSGE",
        begin_date=start_date.strftime("%Y%m%d"),
        end_date=end_date.strftime("%Y%m%d")
    )
    if warehouse is not None:
        print(f"✅ 获取到 {len(warehouse)} 条仓单记录")
        print(warehouse.tail(3))

    # 测试获取主力合约行情
    print("\n=== 测试获取铜主力合约行情 ===")
    main_data = client.get_main_contract_daily(
        contract_object="cu",
        begin_date=start_date.strftime("%Y%m%d"),
        end_date=end_date.strftime("%Y%m%d"),
        exchange_cd="XSGE"
    )
    if main_data is not None:
        print(f"✅ 获取到 {len(main_data)} 条主力合约数据")
        print(main_data.head(3))
