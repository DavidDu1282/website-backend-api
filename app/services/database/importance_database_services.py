from sqlalchemy.ext.asyncio import AsyncSession
from app.models.llm_models import ChatRequest
from app.services.database.embedding_database_services import retrieve_similar_messages
from app.services.llm.llm_utils import _llm_query_helper
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def extract_first_rating(llm_response):
    """Extracts the first number between 1 and 10 from a string."""
    if llm_response is None:
        logger.warning("LLM response is None. Returning None.")
        return None

    match = re.search(r'\b([1-9]|10)\b', llm_response)
    if match:
        try:
            rating = int(match.group(1))
            return rating
        except ValueError:
            logger.warning(f"Could not convert LLM response to integer: {llm_response}")
            return None
    logger.warning(f"No rating found in LLM response: {llm_response}")
    return None


async def calculate_overall_importance(
    db: AsyncSession,
    user_message: str,
    similarity_threshold: float = 0.6,
    top_k: int = 10,
    placeholder_value: float = 0.0,
):
    """
    Calculates an overall importance score based on similar messages.

    Args:
        db: SQLAlchemy database session.
        user_message: The user's input text.
        similarity_threshold: Minimum similarity score for consideration.
        top_k: The number of most similar messages to consider.
        placeholder_value: The value to return if no messages meet the threshold.

    Returns:
        A single float representing the calculated overall importance score,
        or the placeholder_value if no sufficiently similar messages are found.
    """
    try:
        similar_messages = await retrieve_similar_messages(
            db=db,
            query_text=user_message,
            table_name="importance_sample_messages",
            embedding_column_name="embedding",
            return_column_names=["sample_message", "importance_score"],
            top_k=top_k,
        )


        scores_above_threshold = []
        for message_data in similar_messages:
            similarity_score = message_data["similarity_score"]
            original_importance = message_data["importance_score"]

            if similarity_score >= similarity_threshold:
                individual_score = (
                    0.7 * similarity_score + 0.3 * original_importance / 100
                )
                scores_above_threshold.append(individual_score)

        if not scores_above_threshold:
            logger.info(f"No messages above similarity threshold for: '{user_message}'.  Using LLM fallback.")
            prompt = f"""On the scale of 1 to 10, where 1 is purely mundane and 10 is extremely important, rate these messages. Output ONLY the numerical rating.

            Message: I'm feeling good today.
            Rating: 1

            Message: I'm in immediate danger.
            Rating: 10

            Message: I think I might need to go to the hospital.
            Rating: 8

            Message: {user_message}
            Rating:"""

            llm_response = await _llm_query_helper(ChatRequest(session_id="extracting_importance_rating_session", prompt=prompt, model="gemini-2.0-flash-lite"))
            llm_rating = extract_first_rating(llm_response)
            logger.info(f"LLM-based importance rating for '{user_message}': {llm_rating}")
            return llm_rating

        overall_score = sum(scores_above_threshold) / len(scores_above_threshold)
        logger.info(f"Calculated overall importance score for '{user_message}': {overall_score}")
        return overall_score

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return placeholder_value
