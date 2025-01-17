import json

tarot_cards = {}

def load_tarot_data(filepath):
    """
    Load tarot card data from JSON file.
    """
    global tarot_cards
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        tarot_cards.update({card["name"]: card for card in data["cards"]})
