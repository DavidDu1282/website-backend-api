#%%
import json
import random
from PIL import Image
import os

# Load tarot data from optimized JSON file
def load_tarot_data(json_file):
    with open(json_file, "r") as file:
        return json.load(file)["cards"]

# Draw multiple cards with random orientations
def draw_multiple_cards(tarot_data, num_cards):
    drawn_cards = []
    for _ in range(num_cards):
        card = random.choice(tarot_data)
        orientation = random.choice(["upright", "reversed"])
        drawn_cards.append((card, orientation))
    return drawn_cards

# Display tarot card images with orientation
def display_card_images(image_folder, drawn_cards):
    for card, orientation in drawn_cards:
        image_path = os.path.join(image_folder, card["img"])
        if os.path.exists(image_path):
            img = Image.open(image_path)
            if orientation == "reversed":
                img = img.transpose(Image.FLIP_TOP_BOTTOM)  # Flip image for reversed orientation
            img.show()  # Opens the image using the default image viewer
        else:
            print(f"Image not found: {image_path}")

# Print details for multiple cards
def print_multiple_card_readings(drawn_cards, spread=None):
    print(f"\n{'-' * 40}")
    print(f"Spread: {spread if spread else 'Custom'}")
    print(f"{'-' * 40}\n")

    for index, (card, orientation) in enumerate(drawn_cards, start=1):
        if spread:
            print(f"\nPosition: {spread[index - 1]} (Card {index})")
        else:
            print(f"\nCard {index}:")
        
        print(f"Name: {card['name']} ({orientation.capitalize()})")
        print(f"Arcana: {card['arcana']} - {card['suit']}")
        print(f"Keywords: {', '.join(card['keywords'])}")
        
        if orientation == "upright":
            print("\nFortune Telling:")
            for line in card["fortune_telling"]:
                print(f"- {line}")
            print("\nMeanings (Light):")
            for line in card["meanings"]["light"]:
                print(f"- {line}")
        else:  # Reversed orientation
            print("\nReversed Fortune Telling:")
            for line in card["fortune_telling"]:
                print(f"- (Reversed) {line}")
            print("\nMeanings (Shadow):")
            for line in card["meanings"]["shadow"]:
                print(f"- {line}")

        print("\nQuestions to Ask:")
        for question in card["questions_to_ask"]:
            print(f"- {question}")
        print(f"\nAffirmation: {card['affirmation']}")

# Define predefined spreads
def get_spread_definition(spread_type):
    if spread_type == "three_card":
        return ["Past", "Present", "Future"], 3
    elif spread_type == "celtic_cross":
        return [
            "You/The Situation",
            "Crossing You",
            "What's Above You (Your Goal)",
            "What's Below You (Your Foundation)",
            "Past Influences",
            "Future Influences",
            "Your Attitude",
            "Outside Influences",
            "Hopes and Fears",
            "Outcome"
        ], 10
    else:
        return None, 0

# Main program
def main():
    tarot_file = "optimized_tarot.json"  # Path to the optimized tarot data JSON file
    image_folder = "cards"  # Folder containing tarot card images

    # Load data
    tarot_data = load_tarot_data(tarot_file)

    # User chooses a spread
    print("Welcome to the Tarot Reader!")
    print("Choose a spread:")
    print("1. Three-Card Spread (Past, Present, Future)")
    print("2. Celtic Cross (10 cards)")
    print("3. Custom Number of Cards")
    
    choice = int(input("Enter your choice (1/2/3): "))
    
    if choice == 1:
        spread_name, num_cards = get_spread_definition("three_card")
    elif choice == 2:
        spread_name, num_cards = get_spread_definition("celtic_cross")
    elif choice == 3:
        num_cards = int(input("How many cards would you like to draw? "))
        spread_name = None
    else:
        print("Invalid choice. Exiting.")
        return

    # Draw cards
    drawn_cards = draw_multiple_cards(tarot_data, num_cards)

    # Display the cards and readings
    display_card_images(image_folder, drawn_cards)
    print_multiple_card_readings(drawn_cards, spread_name)

if __name__ == "__main__":
    main()
#%%