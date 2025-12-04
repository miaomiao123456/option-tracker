from app.models.database import SessionLocal
from app.models.models import DailyBlueprint
import json

db = SessionLocal()

for date_str in ['2025-11-18', '2025-11-19', '2025-11-23']:
    blueprint = db.query(DailyBlueprint).filter_by(record_date=date_str).first()
    if blueprint and blueprint.parsed_strategies:
        print(f"\n=== {date_str} ===")
        strategies = json.loads(blueprint.parsed_strategies)
        for s in strategies:
            print(f"{s['variety']}: {s['direction']} {s['signal']}")
            print(f"  理由: {s['reason']}")

db.close()
