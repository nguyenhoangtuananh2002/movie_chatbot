from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

class Message(BaseModel):
    message: str

@app.post("/api/chat")
async def chat(msg: Message):
    user_message = msg.message

    try:
        # Step 1: Send request to OpenRouter (works like OpenAI API)
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "deepseek/deepseek-chat-v3.1:free",  
            
            "messages": [
                {
                    "role": "system",
                    "content": """You are a movie assistant.
                    If the user mentions a movie or TV show title, extract it and respond only in JSON:
                    { "intent": "find_movie", "title": "Movie name" }
                    Otherwise, reply normally:
                    { "intent": "chat", "reply": "normal chatbot response" }"""
                },
                {"role": "user", "content": user_message}
            ],
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
        )

        data = response.json()
        
        raw = data["choices"][0]["message"]["content"]

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            # fallback: create a normal chat response
            result = {"intent": "chat", "reply": raw}

        # Step 2: Handle movie search
        if result.get("intent") == "find_movie" and result.get("title"):
            query = result["title"]
            tmdb_url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&query={query}"
            tmdb_response = requests.get(tmdb_url)
            tmdb_data = tmdb_response.json()
            print(tmdb_data)

            if not tmdb_data["results"]:
                return {"reply": f"Sorry, I couldn’t find '{query}'."}

            movie = tmdb_data["results"][0]
            movie_title = movie.get("title") or movie.get("name")
            movie_id = movie.get("id")
            media_type = movie.get("media_type", "movie") 
            movie_url = f"https://www.themoviedb.org/{media_type}/{movie_id}"


            return {
                "reply": f"I found '{movie_title}'!",
                "redirect": movie_url,
            }

        # Step 3: Normal chat
        return {"reply": result.get("reply", "Hi there!")}

    except Exception as e:
        print("Error:", e)
        return {"reply": "Something went wrong."}
