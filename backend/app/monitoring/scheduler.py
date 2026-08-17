from apscheduler.schedulers.background import BackgroundScheduler

from app.database.session import SessionLocal
from app.monitoring.incident_detector import detect_linux_incidents

scheduler = BackgroundScheduler()


def run_detection_job():
    db = SessionLocal()
    try:
        incidents = detect_linux_incidents(db)
        if incidents:
            print(f"[monitoring] {len(incidents)} incident(s) detecte(s) automatiquement")
    finally:
        db.close()


def start_scheduler():
    scheduler.add_job(run_detection_job, "interval", minutes=5, id="linux_incident_detection")
    scheduler.start()