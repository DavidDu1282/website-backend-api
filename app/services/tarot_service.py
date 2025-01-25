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

    # Use request.language to determine the language
    language = request.language if hasattr(request, 'language') else "en"

    # Language-specific prompt_data
    language_prompts = {
        "en": {
            "question": "The user has asked the following question regarding their fortune:",
            "cards_drawn": "To assist in answering, they have drawn the following tarot cards:",
            "analyze_three": "Analyze these cards based on their positions (Past, Present, Future) and their light or shadow meanings. Connect them to the user's question and provide actionable insights.",
            "analyze_celtic": "Analyze the drawn cards in the context of the Celtic Cross spread positions and connect them to the user's question. Provide detailed insights based on the light or shadow meanings of the cards.",
            "analyze_custom": "Analyze these five cards, focusing on their individual and collective meanings. Connect their interpretations to the user's question and provide actionable insights."
        },
        "zh": {
            "question": "用户提出了以下与他们的命运相关的问题：",
            "cards_drawn": "为了帮助解答，他们抽出了以下塔罗牌：",
            "analyze_three": "根据这些牌的位置（过去、现在、未来）及其光明或阴影含义进行分析。 将它们与用户的问题联系起来，并提供可操作的洞察。",
            "analyze_celtic": "根据凯尔特十字牌阵中牌的位置进行分析，并将其与用户的问题联系起来。 基于牌的光明或阴影含义提供详细的洞察。",
            "analyze_custom": "分析这五张牌，重点关注它们的个体和整体含义。将它们的解读与用户的问题联系起来，并提供可操作的洞察。"
        }
    }
    
    prompt_data = language_prompts.get(language, language_prompts["en"])
    print(prompt_data)
    # Generate a tarot analysis prompt based on spread type
    if request.spread in ["Three-Card Spread (Past, Present, Future)", "过去、现在、未来"]:
        card_positions = ["Past", "Present", "Future"] if language == "en" else ["过去", "现在", "未来"]
        print(1)
        prompt = (
            f"{prompt_data['question']}\n"
            f"\"{request.user_context}\"\n\n"
            f"{prompt_data['cards_drawn']}\n\n"
        )
        
        for index, card in enumerate(request.tarot_cards):
            card_data = tarot_cards[card.name]
            prompt += (
                f"{card_positions[index]}: {card_data['name']} ({card.orientation.capitalize()})\n"
                f"  关键词: {', '.join(card_data['keywords'])}\n"
                f"  光明含义: {', '.join(card_data['meanings']['light'])}\n"
                f"  阴影含义: {', '.join(card_data['meanings']['shadow'])}\n"
            )
        prompt += f"\n{prompt_data['analyze_three']}"

    elif request.spread in ["Celtic Cross", "凯尔特十字牌阵"]:
        card_positions = [
            "Present Situation", "Challenge", "Subconscious", "Past Influence",
            "Conscious Goal", "Near Future", "Self", "Environment", "Hopes and Fears", "Outcome"
        ] if language == "en" else [
            "当前情况", "挑战", "潜意识", "过去的影响",
            "显意识的目标", "不久的将来", "自我", "环境", "希望与恐惧", "结果"
        ]
        prompt = (
            f"{prompt_data['question']}\n"
            f"\"{request.user_context}\"\n\n"
            f"{prompt_data['cards_drawn']}\n\n"
        )
        for index, card in enumerate(request.tarot_cards):
            if index < len(card_positions):
                card_data = tarot_cards[card.name]
                prompt += (
                    f"{card_positions[index]}: {card_data['name']} ({card.orientation.capitalize()})\n"
                    f"  关键词: {', '.join(card_data['keywords'])}\n"
                    f"  光明含义: {', '.join(card_data['meanings']['light'])}\n"
                    f"  阴影含义: {', '.join(card_data['meanings']['shadow'])}\n"
                )
        prompt += f"\n{prompt_data['analyze_celtic']}"

    elif request.spread in ["Custom (5 cards)", "自定义（5张牌）"]:
        prompt = (
            f"{prompt_data['question']}\n"
            f"\"{request.user_context}\"\n\n"
            f"{prompt_data['cards_drawn']}\n\n"
        )
        for index, card in enumerate(request.tarot_cards):
            card_data = tarot_cards[card.name]
            prompt += (
                f"牌 {index + 1}: {card_data['name']} ({card.orientation.capitalize()})\n"
                f"  关键词: {', '.join(card_data['keywords'])}\n"
                f"  光明含义: {', '.join(card_data['meanings']['light'])}\n"
                f"  阴影含义: {', '.join(card_data['meanings']['shadow'])}\n"
            )
        prompt += f"\n{prompt_data['analyze_custom']}"

    else:
        raise ValueError(f"Unsupported spread type: {request.spread}")
    print(prompt)
    # Send to LLM
    llm_request = ChatRequest(session_id=request.session_id, prompt=prompt)
    try:
        response = chat_logic(llm_request)
        return {
            "message": "Analysis generated successfully" if language == "en" else "分析生成成功",
            "summary": response["response"]
        }
    except Exception as e:
        raise ValueError(f"Error during LLM processing: {e}" if language == "en" else f"LLM 处理时出错：{e}")
