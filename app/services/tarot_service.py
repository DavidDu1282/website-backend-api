from app.data.tarot import tarot_cards
from app.models.llm import ChatRequest
from app.services.llm_service import chat_logic

def analyze_tarot_logic(request):
    """
    Analyze tarot cards with user context.
    """
    # Validate cards
    for card in request.tarot_cards:
        if card.name not in tarot_cards:
            raise ValueError(f"Invalid card: {card.name}")

    # Enrich cards with data
    enriched_cards = [
        {**tarot_cards[card.name], "orientation": card.orientation}
        for card in request.tarot_cards
    ]

    # Generate a tarot analysis prompt
    card_details = "\n".join(
        [
            f"Card {index + 1}: {card['name']} ({card['orientation'].capitalize()})\n"
            f"  Keywords: {', '.join(card.get('keywords', []))}\n"
            f"  Light: {', '.join(card['meanings']['light'])}\n"
            f"  Shadow: {', '.join(card['meanings']['shadow'])}\n"
            for index, card in enumerate(enriched_cards)
        ]
    )

    prompt  = (
        f"The user has asked the following question regarding their fortune: \n"
        f"\"{request.user_context}\"\n\n"
        f"To assist in answering, they have drawn the following tarot cards:\n\n"
        f"{card_details}\n\n"
        f"Analyze the drawn cards and provide an interpretation that connects their meanings to the user's question. "
        f"Include insights based on the cards' positions and their light or shadow meanings. "
        f"Ensure the response is clear and actionable for the user's context."
    )
    # Send to LLM
    llm_request = ChatRequest(session_id=request.session_id, prompt=prompt)
    try:
        response = chat_logic(llm_request)
        return {
            "message": "Analysis generated successfully",
            "summary": response["response"]
        }
    except Exception as e:
        raise ValueError(f"Error during LLM processing: {e}")