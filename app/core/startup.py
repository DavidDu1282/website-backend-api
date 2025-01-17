from app.data.tarot import load_tarot_data

def startup_event():
    """
    Initialize resources on application startup.
    """
    try:
        load_tarot_data("app/data/optimized_tarot.json")
        print("Tarot data loaded successfully.")
    except Exception as e:
        print(f"Failed to load tarot data: {e}")
        raise RuntimeError("Failed to load tarot data.")
