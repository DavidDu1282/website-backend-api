import json

tarot_cards = {}

def load_tarot_data(filepath):
    """
    Load tarot card data from JSON file and split records into English and Chinese versions.
    """
    global tarot_cards
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
        for card in data["cards"]:
            tarot_cards[card["name"]] = {
                "name": card["name"],
                "number": card["number"],
                "arcana": card["arcana"],
                "suit": card["suit"],
                "img": card["img"],
                "fortune_telling": card["fortune_telling"],
                "keywords": card["keywords"],
                "meanings": {
                    "light": card["meanings"]["light"],
                    "shadow": card["meanings"]["shadow"]
                },
                "archetype": card["archetype"],
                "questions_to_ask": card["questions_to_ask"],
                "affirmation": card["affirmation"]
            }
