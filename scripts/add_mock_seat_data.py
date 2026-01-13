"""
添加模拟席位数据用于测试显示效果
基于真实的席位名称,添加模拟数据
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from app.models.models import InstitutionalPosition
from app.models.database import SessionLocal
from datetime import date, datetime

# 真实的期货公司席位名称 (Top 20常见席位)
REAL_BROKERS = [
    "中信期货有限公司",
    "国泰君安期货有限公司",
    "东证期货有限公司",
    "银河期货有限公司",
    "南华期货股份有限公司",
    "永安期货股份有限公司",
    "光大期货有限公司",
    "浙商期货有限公司",
    "华泰期货有限公司",
    "海通期货股份有限公司",
    "广发期货有限公司",
    "五矿期货有限公司",
    "中粮期货有限公司",
    "申银万国期货有限公司",
    "东方财富期货有限公司",
    "方正中期期货有限公司",
    "招商期货有限公司",
    "瑞达期货股份有限公司",
    "兴证期货有限公司",
    "新湖期货有限公司"
]

def add_mock_seats_for_variety(variety_code: str, variety_name: str):
    """为单个品种添加模拟席位数据"""
    db = SessionLocal()
    try:
        # 删除该品种的旧席位数据(保留市场总持仓)
        db.query(InstitutionalPosition).filter(
            InstitutionalPosition.comm_code == variety_code,
            InstitutionalPosition.record_date == date.today(),
            ~InstitutionalPosition.broker_name.like('%市场总持仓%')
        ).delete()

        # 添加模拟多头席位 (Top 10)
        for i, broker in enumerate(REAL_BROKERS[:10], 1):
            position = InstitutionalPosition(
                comm_code=variety_code,
                broker_name=broker,
                net_position=50000 - i * 3000,  # 递减的持仓量
                position_change=1000 - i * 100,  # 递减的变化
                record_date=date.today(),
                created_at=datetime.now()
            )
            db.add(position)

        # 添加模拟空头席位 (Top 10)
        for i, broker in enumerate(REAL_BROKERS[10:20], 1):
            position = InstitutionalPosition(
                comm_code=variety_code,
                broker_name=broker,
                net_position=-(45000 - i * 2800),  # 负数表示空头
                position_change=-(900 - i * 90),
                record_date=date.today(),
                created_at=datetime.now()
            )
            db.add(position)

        db.commit()
        print(f"✅ {variety_name}({variety_code}): 已添加20条模拟席位数据")

    except Exception as e:
        print(f"❌ {variety_code} 添加失败: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    # 为主要品种添加模拟数据
    varieties = [
        ('CU', '沪铜'),
        ('AG', '沪银'),
        ('AU', '沪金'),
        ('AL', '沪铝'),
        ('ZN', '沪锌'),
        ('RB', '螺纹钢'),
        ('HC', '热卷'),
        ('I', '铁矿石'),
        ('J', '焦炭'),
        ('JM', '焦煤'),
        ('M', '豆粕'),
        ('Y', '豆油'),
        ('P', '棕榈油')
    ]

    print("开始添加模拟席位数据...\n")
    for code, name in varieties:
        add_mock_seats_for_variety(code, name)

    print("\n✅ 所有模拟数据添加完成!")
    print("现在可以访问 http://localhost:8001/frontend.html 查看资金面数据")
