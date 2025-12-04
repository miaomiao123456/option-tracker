import logging
import sys
import os
from datetime import date, datetime

# Add project root to path
sys.path.append(os.getcwd())

from app.models.database import SessionLocal, init_db, engine, Base
from app.models.models import (
    Commodity, FundamentalReport, InstitutionalPosition, 
    TechnicalIndicator, ContractInfo, MarketAnalysisSummary
)
from app.services.analysis import AnalysisService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_test_data(db):
    """Create test data"""
    # 1. Commodity
    comm = Commodity(code="RB", name="螺纹钢", exchange="SHFE")
    db.add(comm)
    
    # 2. Contract Info
    contract = ContractInfo(comm_code="RB", multiplier=10, latest_price=3600)
    db.add(contract)
    
    # 3. Fundamental (Bullish)
    report = FundamentalReport(
        comm_code="RB", source="hzzhqx", sentiment="bull", 
        publish_time=datetime.now()
    )
    db.add(report)
    
    # 4. Capital (Retail Long -> Bearish Signal)
    # 20000 lots * 10 * 3600 = 720,000,000 > 200,000,000
    pos = InstitutionalPosition(
        comm_code="RB", broker_name="东方财富", 
        net_position=20000, record_date=date.today()
    )
    db.add(pos)
    
    # 5. Technical (Contango -> Bearish Signal)
    tech = TechnicalIndicator(
        comm_code="RB", term_structure="contango", 
        record_time=datetime.now()
    )
    db.add(tech)
    
    db.commit()

def test_analysis():
    """Run analysis test"""
    # Re-init DB
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        setup_test_data(db)
        
        service = AnalysisService(db)
        service.run_daily_analysis()
        
        # Verify result
        summary = db.query(MarketAnalysisSummary).filter(
            MarketAnalysisSummary.comm_code == "RB"
        ).first()
        
        if summary:
            print(f"Analysis Result for RB:")
            print(f"Fundamental Score: {summary.fundamental_score} (Expected: 5)")
            print(f"Capital Score: {summary.capital_score} (Expected: -3)")
            print(f"Technical Score: {summary.technical_score} (Expected: -3)")
            print(f"Total Score: {summary.fundamental_score + summary.capital_score + summary.technical_score}")
            print(f"Direction: {summary.total_direction}")
            print(f"Reason: {summary.main_reason}")
        else:
            print("No analysis summary found!")
            
    finally:
        db.close()

if __name__ == "__main__":
    test_analysis()
