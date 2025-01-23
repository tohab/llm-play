from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import random

load_dotenv()

app = Flask(__name__)
CORS(app)

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

def get_target_word():
    try:
        # Try to use system dictionary (common on Unix systems)
        with open('/usr/share/dict/words', 'r') as f:
            words = [word.strip().lower() for word in f.readlines()]
            # Filter valid words (alphabetic, 3-12 characters)
            valid_words = [w for w in words if w.isalpha() and 3 <= len(w) <= 12]
            return random.choice(valid_words)
    except Exception as e:
        print(f"Error loading system dictionary: {e}")
        # Fallback to an extensive word list
        fallback_words = ["apple", "ocean", "music", "light", "dream", "cloud", "earth",
                        "smile", "stone", "water", "heart", "moon", "sun", "tree", 
                        "flower", "river", "mountain", "star", "fire", "wind", "book",
                        "computer", "language", "coffee", "guitar", "castle", "forest",
                        "window", "planet", "mirror", "garden", "secret", "shadow",
                        "winter", "summer", "spring", "autumn", "journey", "mystery",
                        "whisper", "bottle", "letter", "silence", "moment", "history"]
        return random.choice(fallback_words)

TARGET_WORD = get_target_word()

SYSTEM_MESSAGE = {
    "role": "system",
    "content": f"""You are a word guessing game master. The target word is '{TARGET_WORD}'. 
    For each user guess, respond ONLY with a JSON object containing: 
    1. 'percentage' (0-100 number estimating similarity to target)
    2. 'hint' (a cryptic clue related to target)
    Example: {{"percentage": 75, "hint": "It grows on trees"}}
    Do NOT include any other text or formatting."""
}

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    messages = data.get('messages', [])

    filtered_messages = [msg for msg in messages if msg.get("role") != "system"]
    messages_with_system = [SYSTEM_MESSAGE] + filtered_messages

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages_with_system,
            stream=False
        )

        llm_response = response.choices[0].message.content
        
        try:
            json.loads(llm_response)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid response format from AI"}), 500

        return jsonify({"content": llm_response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)