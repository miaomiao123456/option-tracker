import os
from datetime import datetime
from pathlib import Path
from app.models.database import SessionLocal
from app.models.models import DailyBlueprint

def import_images():
    # Path to images
    base_dir = Path("/Users/pm/Documents/期权交易策略/交易可查/images")
    
    if not base_dir.exists():
        print(f"Directory not found: {base_dir}")
        return

    db = SessionLocal()
    count = 0
    
    print(f"Scanning {base_dir}...")
    
    for file in os.listdir(base_dir):
        if file.lower().endswith(('.jpg', '.png', '.jpeg')):
            # Parse date from filename (e.g., 20251117.png)
            try:
                date_str = os.path.splitext(file)[0]
                record_date = datetime.strptime(date_str, "%Y%m%d").date()
                
                # Check if exists
                exists = db.query(DailyBlueprint).filter_by(record_date=record_date).first()
                
                if not exists:
                    file_path = str(base_dir / file)
                    blueprint = DailyBlueprint(
                        image_url=f"file://{file_path}", # Local file URL
                        local_path=file_path,
                        record_date=record_date,
                        parsed_strategies=f"历史归档 - {record_date}",
                        created_at=datetime.now()
                    )
                    db.add(blueprint)
                    count += 1
                    print(f"Imported: {file}")
                else:
                    print(f"Skipped (Exists): {file}")
                    
            except ValueError:
                print(f"Skipped (Invalid Date Format): {file}")
                
    db.commit()
    db.close()
    print(f"Import complete. Added {count} records.")

if __name__ == "__main__":
    import_images()
