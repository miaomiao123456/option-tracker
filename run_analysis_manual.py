import asyncio
import logging
from app.services.analysis import AnalysisService
from app.models.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting manual daily analysis...")
    db = SessionLocal()
    try:
        service = AnalysisService(db)
        service.run_daily_analysis()
        logger.info("Daily analysis completed.")
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
