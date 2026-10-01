import os
import time
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI, OpenAIError

load_dotenv()

client = OpenAI(
    api_key=os.getenv("API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

MODEL = "gemini-2.5-flash"
SYSTEM_PROMPT = "You are a friendly AI assistant. Keep your answers short and clear."

app = FastAPI()


class Message(BaseModel):
    role: str      # "user" ya "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]   # browser se poori history aati hai


@app.get("/")
def home():
    return FileResponse("index.html")


@app.post("/chat")
def chat(req: ChatRequest):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [m.model_dump() for m in req.messages]

    for attempt in range(1, 4):
        try:
            response = client.chat.completions.create(model=MODEL, messages=messages)
            return {"reply": response.choices[0].message.content}
        except OpenAIError:
            if attempt < 3:
                time.sleep(2 * attempt)

    raise HTTPException(status_code=503, detail="AI service is busy. Please try again.")