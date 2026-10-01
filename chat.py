import os
import time
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

load_dotenv()

client = OpenAI(
    api_key=os.getenv("API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = "You are a friendly AI assistant. Keep your answers short and clear."

# History ki pehli entry system prompt hai
history = [{"role": "system", "content": SYSTEM_PROMPT}]


def ask_ai(messages, retries=3):
    """AI ko messages bhejta hai. Fail ho to retries tak dobara koshish karta hai."""
    for attempt in range(1, retries + 1):
        try:
            response = client.chat.completions.create(model=MODEL, messages=messages)
            return response.choices[0].message.content
        except OpenAIError:
            print(f"(Server problem, attempt {attempt}/{retries})")
            if attempt < retries:
                time.sleep(2 * attempt)  # pehle 2 sec, phir 4 sec ruko
    return None  # sab koshishein fail ho gayin


print("Chatbot ready. Type 'quit' to exit.")

while True:
    user_message = input("You: ").strip()

    if not user_message:
        continue  # khali message ignore karo

    if user_message.lower() in ("quit", "exit"):
        print("Goodbye!")
        break

    history.append({"role": "user", "content": user_message})

    reply = ask_ai(history)

    if reply is None:
        print("AI: Sorry, the AI service is busy right now. Please try again.")
        history.pop()  # fail hone wala message history se hata do
        continue

    history.append({"role": "assistant", "content": reply})
    print("AI:", reply)