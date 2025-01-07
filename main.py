from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import aisuite as ai

app = FastAPI()

# Model for incoming request
class LLMRequest(BaseModel):
    model: str
    messages: list

@app.post("/api/llm/chat")
async def chat(request: LLMRequest):
    try:
        client = ai.Client()
        response = client.chat.completions.create(
            model=request.model,
            messages=request.messages,
        )
        return {"response": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
