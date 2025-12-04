"""
初始化数据源配置
注册系统中所有数据源
"""
from app.services.data_collector import register_data_source


def init_all_data_sources():
    """注册所有数据源"""

    print("=" * 60)
    print("初始化数据源配置")
    print("=" * 60)

    # ==================== 基本面数据源 ====================

    # 1. 智汇期讯 - 多空全景
    register_data_source(
        source_name="智汇期讯-多空全景",
        source_type="spider",
        category="fundamental",
        provider="智汇期讯网",
        url="https://zhqx.cjis.cn/quote/sentiment",
        description="期货研报机构情绪数据，包含看多/看空/中性观点统计",
        update_frequency="daily",
        cron_expression="0 20 30 * * *",  # 每天20:30
        data_fields=[
            "variety_code", "variety_name", "excessive_num",
            "neutral_num", "empty_num", "main_sentiment"
        ],
        dependencies=[]
    )

    # 2. 智汇期讯 - 价格数据
    register_data_source(
        source_name="智汇期讯-价格数据",
        source_type="spider",
        category="fundamental",
        provider="智汇期讯网",
        url="https://zhqx.cjis.cn/quote/price",
        description="期货合约价格和涨跌幅数据",
        update_frequency="daily",
        cron_expression="0 20 32 * * *",
        data_fields=["variety_code", "price", "change_pct", "volume"],
        dependencies=[]
    )

    # ==================== 技术面数据源 ====================

    # 3. 交易可查 - 每日蓝图
    register_data_source(
        source_name="交易可查-每日蓝图",
        source_type="spider",
        category="technical",
        provider="交易可查网",
        url="https://www.jiaoyikecha.com",
        description="每日交易蓝图图片，包含散户vs机构持仓对比",
        update_frequency="daily",
        cron_expression="0 21 0 * * *",  # 每天21:00
        data_fields=["image_url", "local_path", "record_date"],
        dependencies=[]
    )

    # 4. 百度OCR - 蓝图识别
    register_data_source(
        source_name="百度OCR-文字识别",
        source_type="service",
        category="technical",
        provider="百度智能云",
        url="https://aip.baidubce.com/rest/2.0/ocr/v1/accurate",
        description="高精度OCR文字识别，用于解析蓝图图片",
        update_frequency="realtime",
        data_fields=["words_result"],
        dependencies=["交易可查-每日蓝图"]
    )

    # 5. LLM - 策略分析
    register_data_source(
        source_name="LLM-策略解析",
        source_type="service",
        category="technical",
        provider="OpenAI/Gemini",
        url="https://api.openai.com/v1/chat/completions",
        description="AI大模型，用于分析OCR文字并生成交易策略",
        update_frequency="realtime",
        data_fields=["strategies"],
        dependencies=["百度OCR-文字识别"]
    )

    # ==================== 资金面数据源 ====================

    # 6. openvlab - 期权资金流向
    register_data_source(
        source_name="openvlab-期权流向",
        source_type="spider",
        category="capital",
        provider="openvlab.cn",
        url="https://www.openvlab.cn/option-flow",
        description="期权资金流向数据，包含看涨/看跌期权成交和持仓",
        update_frequency="hourly",
        cron_expression="0 */1 * * * *",  # 每小时
        data_fields=[
            "comm_code", "direction", "net_flow", "volume",
            "open_interest", "change_oi"
        ],
        dependencies=[]
    )

    # 7. 融达期货 - 机构持仓
    register_data_source(
        source_name="融达期货-机构持仓",
        source_type="spider",
        category="capital",
        provider="融达期货",
        url="http://www.rongdaqh.com.cn",
        description="机构席位持仓数据",
        update_frequency="daily",
        cron_expression="0 21 0 * * *",
        data_fields=["variety", "long_position", "short_position", "net_position"],
        dependencies=[]
    )

    # 8. 容大期货 - 技术指标
    register_data_source(
        source_name="容大期货-技术指标",
        source_type="spider",
        category="technical",
        provider="容大期货",
        url="http://www.rdqh.com",
        description="期货技术分析指标",
        update_frequency="daily",
        cron_expression="0 21 5 * * *",
        data_fields=["variety", "rsi", "macd", "kdj", "ma"],
        dependencies=[]
    )

    # ==================== 消息面数据源 ====================

    # 9. 方期看盘 - 合约信息
    register_data_source(
        source_name="方期看盘-合约信息",
        source_type="spider",
        category="fundamental",
        provider="方期看盘",
        url="https://www.fangqikanpan.com",
        description="期货合约基本信息",
        update_frequency="weekly",
        cron_expression="0 0 9 * * 1",  # 每周一9:00
        data_fields=["contract_code", "variety", "exchange", "expiry_date"],
        dependencies=[]
    )

    # ==================== 第三方API数据源 ====================

    # 10. akshare - 行情数据（示例）
    register_data_source(
        source_name="akshare-期货行情",
        source_type="api",
        category="fundamental",
        provider="akshare",
        url="https://akshare.akfamily.xyz",
        description="Python API，提供期货行情、持仓、成交等数据",
        update_frequency="realtime",
        data_fields=["open", "high", "low", "close", "volume", "oi"],
        dependencies=[]
    )

    # 11. tushare - 财经数据（备用）
    register_data_source(
        source_name="tushare-财经数据",
        source_type="api",
        category="fundamental",
        provider="tushare",
        url="https://tushare.pro",
        description="财经数据接口，提供宏观经济、行业数据等",
        update_frequency="daily",
        data_fields=["gdp", "cpi", "ppi", "inventory"],
        dependencies=[]
    )

    # ==================== 本地文件数据源 ====================

    # 12. 本地蓝图图片
    register_data_source(
        source_name="本地-蓝图图片库",
        source_type="file",
        category="technical",
        provider="本地存储",
        url="/Users/pm/Documents/期权交易策略/交易可查/images",
        description="本地存储的蓝图图片文件",
        update_frequency="manual",
        data_fields=["filename", "date", "size"],
        dependencies=[]
    )

    print("=" * 60)
    print("✅ 数据源初始化完成")
    print("=" * 60)


if __name__ == "__main__":
    init_all_data_sources()
