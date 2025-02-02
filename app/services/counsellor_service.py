from app.models.llm import ChatRequest
from app.services.llm_service import chat_logic

def analyse_counsellor_request(request):
    """
    Analyze user input and generate a response using the LLM.
    """
    # Validate user message
    if not hasattr(request, 'message') or not request.message.strip():
        raise ValueError("Invalid input: Message cannot be empty")

    # Determine language
    language = request.language if hasattr(request, 'language') else "en"
    
    # Define system messages for different languages
    system_messages = {
        "en": "The user has shared a concern. Provide a thoughtful and empathetic response:",
        "zh": "用户分享了一个烦恼，请提供一个富有同理心和深思熟虑的回应：",
        "zh_TW": "使用者分享了一個煩惱，請提供一個富有同理心和深思熟慮的回應："
    }
    
    prompt = f"{system_messages.get(language, system_messages['en'])}\n\n" \
             f"User's concern: \"{request.message}\"\n\n"
    
    # Prepare request for LLM
    llm_request = ChatRequest(session_id=request.session_id, prompt=prompt)
    
    try:
        response = chat_logic(llm_request)
        return {
            "message": "Response generated successfully" if language == "en" else "回应生成成功",
            "response": response["response"]
        }
    except Exception as e:
        raise ValueError(f"Error during LLM processing: {e}" if language == "en" else f"LLM 处理时出错：{e}")
