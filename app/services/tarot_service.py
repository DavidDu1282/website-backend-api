# app/services/tarot_service.py
from app.data.tarot import tarot_cards
from app.models.llm import ChatRequest
from app.services.llm_service import chat_logic
from sqlalchemy.orm import Session

from fastapi import HTTPException, Request
from jose import JWTError, jwt
from app.models.tarot_reading_history import TarotReadingHistory
from app.core.config import Settings
import json
from datetime import datetime
import logging
from typing import AsyncGenerator

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def analyze_tarot_logic(request, db: Session, user) -> AsyncGenerator[str, None]:
    """
    Analyze tarot cards with user context based on the spread type.
    Streams the LLM response.
    """
    logger.info("Starting tarot service")
    logger.debug(f"Full Request: {request.__dict__}")
    # Validate cards
    for card in request.tarot_cards:
        if card.name not in tarot_cards:
            raise ValueError(f"Invalid card: {card.name}")

    language = request.language if hasattr(request, 'language') else "en"

    # Language-specific prompt_data
    language_prompts = {
        "en": {
            "question": "The user has asked the following question regarding their fortune:",
            "cards_drawn": "To assist in answering, they have drawn the following tarot cards:",
            "analyze_three": "Analyze these cards based on their positions (Past, Present, Future) and their light or shadow meanings. Connect them to the user's question and provide actionable insights.",
            "analyze_celtic": "Analyze the drawn cards in the context of the Celtic Cross spread positions and connect them to the user's question. Provide detailed insights based on the light or shadow meanings of the cards.",
            "analyze_custom": "Analyze these five cards, focusing on their individual and collective meanings. Connect their interpretations to the user's question and provide actionable insights.",
            "card_label": "Card",
            "keywords_label": "Keywords",
            "light_meanings_label": "Light Meanings",
            "shadow_meanings_label": "Shadow Meanings",
            "past_label": "Past",
            "present_label": "Present",
            "future_label": "Future",
            "message_success": "Analysis generated successfully",
            "error_llm": "Error during LLM processing: "
        },
        "zh": {
            "question": "用户提出了以下与他们的命运相关的问题：",
            "cards_drawn": "为了帮助解答，他们抽出了以下塔罗牌：",
            "analyze_three": "根据这些牌的位置（过去、现在、未来）及其光明或阴影含义进行分析。 将它们与用户的问题联系起来，并提供可操作的洞察。",
            "analyze_celtic": "根据凯尔特十字牌阵中牌的位置进行分析，并将其与用户的问题联系起来。 基于牌的光明或阴影含义提供详细的洞察。",
            "analyze_custom": "分析这五张牌，重点关注它们的个体和整体含义。将它们的解读与用户的问题联系起来，并提供可操作的洞察。",
            "card_label": "牌",
            "keywords_label": "关键词",
            "light_meanings_label": "光明含义",
            "shadow_meanings_label": "阴影含义",
            "past_label": "过去",
            "present_label": "现在",
            "future_label": "未来",
            "message_success": "分析生成成功",
            "error_llm": "LLM 处理时出错："
        },
        "zh_TW": {
            "question": "使用者提出了以下與他們的命運相關的問題：",
            "cards_drawn": "為了幫助解答，他們抽出了以下塔羅牌：",
            "analyze_three": "根據這些牌的位置（過去、現在、未來）及其光明或陰影含義進行分析。 將它們與使用者的問題聯繫起來，並提供可操作的洞察。",
            "analyze_celtic": "根據凱爾特十字牌陣中牌的位置進行分析，並將其與使用者的問題聯繫起來。 基於牌的光明或陰影含義提供詳細的洞察。",
            "analyze_custom": "分析這五張牌，重點關注它們的個體和整體含義。將它們的解讀與使用者的問題聯繫起來，並提供可操作的洞察。",
            "card_label": "牌",
            "keywords_label": "關鍵詞",
            "light_meanings_label": "光明含義",
            "shadow_meanings_label": "陰影含義",
            "past_label": "過去",
            "present_label": "現在",
            "future_label": "未來",
            "message_success": "分析生成成功",
            "error_llm": "LLM 處理時出錯："
        }
    }

    prompt_data = language_prompts.get(language, language_prompts["en"])

    # Generate a tarot analysis prompt based on spread type
    if request.spread in ["Three-Card Spread (Past, Present, Future)", "过去、现在、未来", "過去、現在、未來"]:
        card_positions = [
            prompt_data["past_label"],
            prompt_data["present_label"],
            prompt_data["future_label"]
        ]

        prompt = (
            f"{prompt_data['question']}\n"
            f"\"{request.user_context}\"\n\n"
            f"{prompt_data['cards_drawn']}\n\n"
        )

        for index, card in enumerate(request.tarot_cards):
            card_data = tarot_cards[card.name]
            prompt += (
                f"{card_positions[index]}: {card_data['name']} ({card.orientation.capitalize()})\n"
                f"  {prompt_data['keywords_label']}: {', '.join(card_data['keywords'])}\n"
                f"  {prompt_data['light_meanings_label']}: {', '.join(card_data['meanings']['light'])}\n"
                f"  {prompt_data['shadow_meanings_label']}: {', '.join(card_data['meanings']['shadow'])}\n"
            )
        prompt += f"\n{prompt_data['analyze_three']}"

    elif request.spread in ["Celtic Cross", "凯尔特十字牌阵", "凱爾特十字牌陣"]:
        card_positions = {
            "en": [
                "Present Situation", "Challenge", "Subconscious", "Past Influence",
                "Conscious Goal", "Near Future", "Self", "Environment", "Hopes and Fears", "Outcome"
            ],
            "zh": [
                "当前情况", "挑战", "潜意识", "过去的影响",
                "显意识的目标", "不久的将来", "自我", "环境", "希望与恐惧", "结果"
            ],
            "zh_TW": [
                "目前情況", "挑戰", "潛意識", "過去的影響",
                "顯意識的目標", "不久的將來", "自我", "環境", "希望與恐懼", "結果"
            ]
        }[language]

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
                    f"  {prompt_data['keywords_label']}: {', '.join(card_data['keywords'])}\n"
                    f"  {prompt_data['light_meanings_label']}: {', '.join(card_data['meanings']['light'])}\n"
                    f"  {prompt_data['shadow_meanings_label']}: {', '.join(card_data['meanings']['shadow'])}\n"
                )
        prompt += f"\n{prompt_data['analyze_celtic']}"

    elif request.spread in ["Custom (5 cards)", "自定义（5张牌）", "自定義（5張牌）"]:
        prompt = (
            f"{prompt_data['question']}\n"
            f"\"{request.user_context}\"\n\n"
            f"{prompt_data['cards_drawn']}\n\n"
        )
        for index, card in enumerate(request.tarot_cards):
            card_data = tarot_cards[card.name]
            prompt += (
                f"{prompt_data['card_label']} {index + 1}: {card_data['name']} ({card.orientation.capitalize()})\n"
                f"  {prompt_data['keywords_label']}: {', '.join(card_data['keywords'])}\n"
                f"  {prompt_data['light_meanings_label']}: {', '.join(card_data['meanings']['light'])}\n"
                f"  {prompt_data['shadow_meanings_label']}: {', '.join(card_data['meanings']['shadow'])}\n"
            )
        prompt += f"\n{prompt_data['analyze_custom']}"

    else:
        raise ValueError(f"Unsupported spread type: {request.spread}")

    logger.info(prompt)
    llm_request = ChatRequest(session_id=request.session_id, prompt=prompt)

    response_chunks = []  # Accumulate for database
    try:
        async for chunk in chat_logic(llm_request): # Await the async generator
            # logger.info(f"Received chunk: {chunk}")
            response_chunks.append(chunk)
            yield chunk  # Stream the chunk directly
    except Exception as e:
        logger.error(f"Error during LLM processing: {e}", exc_info=True)
        error_message = f"{prompt_data['error_llm']}{e}"
        yield error_message #yield error to client
        raise HTTPException(status_code=500, detail=error_message)
    logger.info("Received full response from LLM service.")

    full_response = "".join(response_chunks)

    if user:
        try:
            user_id_int = user.id
            cards_drawn_serialized = json.dumps([{"name": card.name, "orientation": card.orientation} for card in request.tarot_cards])


            # --- LOGGING BEFORE DATABASE INTERACTION ---
            logger.info("--- Preparing to store Tarot Reading ---")
            logger.info(f"  user_id: {user_id_int} (type: {type(user_id_int)})")
            logger.info(f"  reading_date: {datetime.utcnow()} (type: {type(datetime.utcnow())})")
            logger.info(f"  cards_drawn: {cards_drawn_serialized} (type: {type(cards_drawn_serialized)})")
            logger.info(f"  interpretation: {full_response} (type: {type(full_response)})")
            logger.info(f"  spread: {request.spread} (type: {type(request.spread)})")
            logger.info(f"  user_context: {request.user_context} (type: {type(request.user_context)})")
            logger.info("----------------------------------------")

            tarot_reading = TarotReadingHistory(
                user_id=user_id_int,
                reading_date=datetime.utcnow(),
                cards_drawn=cards_drawn_serialized,
                interpretation=full_response,  # Use accumulated response
                spread=request.spread,
                user_context=request.user_context
            )

            db.add(tarot_reading)
            db.commit()
        except Exception as e:
            logger.exception(f"Error during database operation: {e}")
            #  Don't re-raise if we've already streamed a response
