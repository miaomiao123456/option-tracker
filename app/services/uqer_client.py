"""
优矿(uqer.datayes.com) API 客户端
用于访问优矿平台的期货数据
"""
import requests
import pandas as pd
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date

logger = logging.getLogger(__name__)


class UqerClient:
    """优矿API客户端"""

    def __init__(self, token: str):
        """
        初始化优矿客户端
        Args:
            token: 优矿API Token
        """
        self.token = token
        self.base_url = "https://api.datayes.com/api"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def _request(self, endpoint: str, params: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """
        发送API请求
        Args:
            endpoint: API端点
            params: 请求参数
        Returns:
            pandas DataFrame 或 None
        """
        try:
            url = f"{self.base_url}/{endpoint}"
            logger.info(f"请求URL: {url}")
            logger.info(f"请求参数: {params}")

            response = requests.get(url, headers=self.headers, params=params, timeout=30)

            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应内容前500字符: {response.text[:500]}")

            response.raise_for_status()

            data = response.json()

            # 检查返回状态
            if data.get("retCode") != 1:
                logger.error(f"API返回错误: retCode={data.get('retCode')}, retMsg={data.get('retMsg')}")
                logger.error(f"完整响应: {data}")
                return None

            # 转换为DataFrame
            if "data" in data and data["data"]:
                df = pd.DataFrame(data["data"])
                return df
            else:
                logger.warning(f"API返回空数据")
                return pd.DataFrame()

        except requests.RequestException as e:
            logger.error(f"API请求失败: {e}")
            return None
        except Exception as e:
            logger.error(f"数据处理失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_futures_contracts(
        self,
        ticker: Optional[str] = None,
        exchange_cd: str = "XSGE",
        contract_status: str = "1",
        contract_object: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        获取期货合约基本信息 (DataAPI.FutuGet)

        Args:
            ticker: 合约交易代码,如 "au2506"
            exchange_cd: 交易所代码 XSGE(上期所)/XDCE(大商所)/XZCE(郑商所)/CCFX(中金所)
            contract_status: 合约状态 1=上市交易
            contract_object: 合约标的,如 "cu"(铜)

        Returns:
            包含合约信息的DataFrame,字段包括:
            - secID: 证券编码
            - ticker: 合约代码
            - contractObject: 合约标的
            - exchangeCD: 交易所
            - lastTradeDate: 最后交易日
            - contMultNum: 合约乘数
            等
        """
        params = {
            "exchangeCD": exchange_cd,
            "contractStatus": contract_status
        }

        if ticker:
            params["ticker"] = ticker
        if contract_object:
            params["contractObject"] = contract_object

        df = self._request("market/getFutu", params)
        return df

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
            ticker: 合约代码,如 "au2506"
            trade_date: 交易日期 YYYYMMDD
            begin_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            exchange_cd: 交易所代码

        Returns:
            包含日行情的DataFrame,字段包括:
            - tradeDate: 交易日期
            - ticker: 合约代码
            - openPrice: 开盘价
            - highestPrice: 最高价
            - lowestPrice: 最低价
            - closePrice: 收盘价
            - settlPrice: 结算价
            - turnoverVol: 成交量
            - turnoverValue: 成交金额
            - openInt: 持仓量
            - CHG: 涨跌
            - CHG1: 涨跌幅
            等
        """
        params = {}

        if ticker:
            params["ticker"] = ticker
        if trade_date:
            params["tradeDate"] = trade_date
        if begin_date:
            params["beginDate"] = begin_date
        if end_date:
            params["endDate"] = end_date
        if exchange_cd:
            params["exchangeCD"] = exchange_cd

        df = self._request("market/getMktFutd", params)
        return df

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
            包含仓单信息的DataFrame,字段包括:
            - tradeDate: 交易日期
            - contractObject: 品种代码
            - exchangeCD: 交易市场
            - prevWarehouseStock: 上期仓单量
            - warehouseStock: 本期仓单量
            - warehouseStockChg: 仓单量增减
            等
        """
        params = {}

        if contract_object:
            params["contractObject"] = contract_object
        if exchange_cd:
            params["exchangeCD"] = exchange_cd
        if begin_date:
            params["beginDate"] = begin_date
        if end_date:
            params["endDate"] = end_date

        df = self._request("market/getMktFutWRd", params)
        return df

    def get_main_contract_daily(
        self,
        contract_object: str,
        trade_date: Optional[str] = None,
        begin_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        获取主力合约日行情

        通过获取某个标的所有合约,按持仓量筛选出主力合约

        Args:
            contract_object: 合约标的,如 "cu"
            trade_date: 交易日期 YYYYMMDD
            begin_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            主力合约的日行情数据
        """
        # 先获取该标的所有合约
        contracts = self.get_futures_contracts(contract_object=contract_object)

        if contracts is None or contracts.empty:
            logger.warning(f"未找到 {contract_object} 的合约信息")
            return None

        # 获取所有合约的行情数据
        all_data = []
        for _, contract in contracts.iterrows():
            ticker = contract.get("ticker")
            if not ticker:
                continue

            df = self.get_futures_daily(
                ticker=ticker,
                trade_date=trade_date,
                begin_date=begin_date,
                end_date=end_date
            )

            if df is not None and not df.empty:
                all_data.append(df)

        if not all_data:
            return None

        # 合并所有数据
        combined_df = pd.concat(all_data, ignore_index=True)

        # 按日期分组,取持仓量最大的合约作为主力合约
        if "openInt" in combined_df.columns and "tradeDate" in combined_df.columns:
            main_contracts = combined_df.loc[
                combined_df.groupby("tradeDate")["openInt"].idxmax()
            ]
            return main_contracts

        return combined_df


# 创建一个全局客户端实例(需要在使用前初始化)
_uqer_client: Optional[UqerClient] = None


def init_uqer_client(token: str) -> UqerClient:
    """
    初始化全局优矿客户端
    Args:
        token: 优矿API Token
    Returns:
        UqerClient实例
    """
    global _uqer_client
    _uqer_client = UqerClient(token)
    return _uqer_client


def get_uqer_client() -> Optional[UqerClient]:
    """
    获取全局优矿客户端实例
    Returns:
        UqerClient实例或None
    """
    return _uqer_client


# 测试代码
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 需要先配置token
    token = "your_uqer_token_here"
    client = UqerClient(token)

    # 测试获取铜合约信息
    print("=== 测试获取铜合约信息 ===")
    contracts = client.get_futures_contracts(contract_object="cu", exchange_cd="XSGE")
    if contracts is not None:
        print(contracts.head())

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
        print(warehouse)

    # 测试获取主力合约行情
    print("\n=== 测试获取铜主力合约行情 ===")
    today = datetime.now().strftime("%Y%m%d")
    main_data = client.get_main_contract_daily(contract_object="cu", trade_date=today)
    if main_data is not None:
        print(main_data)
