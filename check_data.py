from app.models.database import SessionLocal
from app.models.models import *
from datetime import date

db = SessionLocal()
today = date.today()

print(f'=== {today} 数据统计 ===')
print(f'基本面报告: {db.query(FundamentalReport).count()} 条')
print(f'机构持仓: {db.query(InstitutionalPosition).count()} 条')
print(f'技术指标: {db.query(TechnicalIndicator).count()} 条')
print(f'期权流向: {db.query(OptionFlow).count()} 条')
print(f'分析汇总: {db.query(MarketAnalysisSummary).filter_by(date=today).count()} 个品种')

summaries = db.query(MarketAnalysisSummary).filter_by(date=today).all()
print(f'\n品种列表 (前10个):')
for s in summaries[:10]:
    total = s.fundamental_score + s.capital_score + s.technical_score + s.message_score
    direction = s.total_direction.value if s.total_direction else "中性"
    print(f'  {s.comm_code}: {direction} (总分: {total})')

db.close()
