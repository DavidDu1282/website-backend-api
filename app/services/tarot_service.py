from app.data.tarot import tarot_cards
from app.models.llm import ChatRequest
from app.services.llm_service import chat_logic

def analyze_tarot_logic(request):
    """
    Analyze tarot cards with user context based on the spread type.
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

    # Generate a tarot analysis prompt based on spread type
    if request.spread == "Three-Card Spread (Past, Present, Future)":
        card_positions = ["Past", "Present", "Future"]
        prompt = (
            f"用户提出了以下与他们的命运相关的问题：\n"
            f"\"{request.user_context}\"\n\n"
            f"为了帮助解答，他们抽出了以下塔罗牌：\n\n"
        )
        for index, card in enumerate(enriched_cards):
            prompt += (
                f"{card_positions[index]}: {card['name']} ({card['orientation'].capitalize()})\n"
                f"  关键词: {', '.join(card.get('keywords', []))}\n"
                f"  光明含义: {', '.join(card['meanings']['light'])}\n"
                f"  阴影含义: {', '.join(card['meanings']['shadow'])}\n"
            )
        prompt += (
            "\n根据这些牌的位置（过去、现在、未来）及其光明或阴影含义进行分析。 "
            "将它们与用户的问题联系起来，并提供可操作的洞察。"
        )

    elif request.spread == "Celtic Cross":
        card_positions = [
            "当前情况", "挑战", "潜意识", "过去的影响",
            "显意识的目标", "不久的将来", "自我", "环境", "希望与恐惧", "结果"
        ]
        prompt = (
            f"用户提出了以下与他们的命运相关的问题：\n"
            f"\"{request.user_context}\"\n\n"
            f"为了帮助解答，他们在凯尔特十字牌阵中抽出了以下塔罗牌：\n\n"
        )
        for index, card in enumerate(enriched_cards):
            if index < len(card_positions):
                prompt += (
                    f"{card_positions[index]}: {card['name']} ({card['orientation'].capitalize()})\n"
                    f"  关键词: {', '.join(card.get('keywords', []))}\n"
                    f"  光明含义: {', '.join(card['meanings']['light'])}\n"
                    f"  阴影含义: {', '.join(card['meanings']['shadow'])}\n"
                )
        prompt += (
            "\n根据凯尔特十字牌阵中牌的位置进行分析，并将其与用户的问题联系起来。 "
            "基于牌的光明或阴影含义提供详细的洞察。"
        )

    elif request.spread == "Custom (5 cards)":
        prompt = (
            f"用户提出了以下与他们的命运相关的问题：\n"
            f"\"{request.user_context}\"\n\n"
            f"为了帮助解答，他们抽出了以下五张塔罗牌：\n\n"
        )
        for index, card in enumerate(enriched_cards):
            prompt += (
                f"牌 {index + 1}: {card['name']} ({card['orientation'].capitalize()})\n"
                f"  关键词: {', '.join(card.get('keywords', []))}\n"
                f"  光明含义: {', '.join(card['meanings']['light'])}\n"
                f"  阴影含义: {', '.join(card['meanings']['shadow'])}\n"
            )
        prompt += (
            "\n分析这五张牌，重点关注它们的个体和整体含义。将它们的解读与用户的问题联系起来，并提供可操作的洞察。"
        )

    else:
        raise ValueError(f"不支持的牌阵类型：{request.spread}")

    # Send to LLM
    llm_request = ChatRequest(session_id=request.session_id, prompt=prompt)
    try:
        response = chat_logic(llm_request)
        return {
            "message": "分析生成成功",
            "summary": response["response"]
        }
    except Exception as e:
        raise ValueError(f"LLM 处理时出错：{e}")
