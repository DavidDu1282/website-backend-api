from app.data.tarot import load_tarot_data
from app.services.llm_service import cleanup_expired_sessions

def startup_event():
    """
    Initialize resources on application startup.
    """
    try:
        load_tarot_data("app/data/optimized_tarot_translated.json")
        print("Tarot data loaded successfully.")
        cleanup_expired_sessions()
    except Exception as e:
        print(f"Failed to load tarot data: {e}")
        raise RuntimeError("Failed to load tarot data.")
