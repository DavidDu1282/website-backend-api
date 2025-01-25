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
            # English version
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

            # # Chinese version
            # tarot_cards[card["nameZh"]] = {
            #     "name": card["nameZh"],
            #     "number": card["number"],
            #     "arcana": card["arcana"],
            #     "suit": card["suit"],
            #     "img": card["img"],
            #     "fortune_telling": card.get("fortune_tellingZh", card["fortune_telling"]),
            #     "keywords": card.get("keywordsZh", card["keywords"]),
            #     "meanings": {
            #         "light": card["meanings"].get("lightZh", card["meanings"]["light"]),
            #         "shadow": card["meanings"].get("shadowZh", card["meanings"]["shadow"])
            #     },
            #     "archetype": card.get("archetypeZh", card["archetype"]),
            #     "questions_to_ask": card.get("questions_to_askZh", card["questions_to_ask"]),
            #     "affirmation": card["affirmation"]
            # }
