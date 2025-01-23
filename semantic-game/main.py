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

def get_related_words(seed_word, difficulty):
    """Get semantically related words based on seed word and difficulty"""
    # Define tighter similarity thresholds based on difficulty
    similarity_ranges = {
        'easy': (0.9, 1.0),   # Very similar words, same category
        'medium': (0.8, 0.9), # Similar words, same general domain
        'hard': (0.7, 0.8)    # Related words, same broad context
    }
    
    # Get similarity range based on difficulty
    min_sim, max_sim = similarity_ranges.get(difficulty, (0.8, 0.9))
    
    # Generate more specific prompt for Deepseek
    prompt = f"""Generate 10 words that are semantically related to '{seed_word}'.
    The words should:
    1. Have a similarity score between {min_sim} and {max_sim}
    2. Be in the same semantic category and part of speech
    3. Exist in the same conceptual universe
    4. Be appropriate for a word guessing game
    5. Be common enough for most players to know
    Return ONLY a JSON array of words, no other text or formatting."""
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            stream=False
        )
        
        # Parse response and return words
        words = json.loads(response.choices[0].message.content)
        return [w.lower() for w in words if w.isalpha() and 3 <= len(w) <= 12]
    except Exception as e:
        print(f"Error generating related words: {e}")
        return []

def get_target_word(seed_word=None, difficulty='medium'):
    """Get target word based on seed word and difficulty"""
    if seed_word:
        # Get related words based on seed and difficulty
        related_words = get_related_words(seed_word, difficulty)
        if related_words:
            return random.choice(related_words)
    
    # Fallback to random word if no seed or error
    try:
        with open('/usr/share/dict/words', 'r') as f:
            words = [word.strip().lower() for word in f.readlines()]
            valid_words = [w for w in words if w.isalpha() and 3 <= len(w) <= 12]
            return random.choice(valid_words)
    except Exception as e:
        print(f"Error loading system dictionary: {e}")
        fallback_words = ["apple", "ocean", "music", "light", "dream", "cloud", "earth",
                        "smile", "stone", "water", "heart", "moon", "sun", "tree", 
                        "flower", "river", "mountain", "star", "fire", "wind", "book",
                        "computer", "language", "coffee", "guitar", "castle", "forest",
                        "window", "planet", "mirror", "garden", "secret", "shadow",
                        "winter", "summer", "spring", "autumn", "journey", "mystery",
                        "whisper", "bottle", "letter", "silence", "moment", "history"]
        return random.choice(fallback_words)

TARGET_WORD = None
CURRENT_SEED = None
CURRENT_DIFFICULTY = 'medium'

@app.route('/start-game', methods=['POST'])
def start_game():
    global TARGET_WORD, CURRENT_SEED, CURRENT_DIFFICULTY, SYSTEM_MESSAGE
    data = request.json
    seed_word = data.get('seed_word')
    difficulty = data.get('difficulty', 'medium')
    
    # Get new target word based on seed and difficulty
    TARGET_WORD = get_target_word(seed_word, difficulty)
    CURRENT_SEED = seed_word
    CURRENT_DIFFICULTY = difficulty
    
    # Update system message
    SYSTEM_MESSAGE = {
        "role": "system",
        "content": f"""You are a word guessing game master. The target word is '{TARGET_WORD}' 
        and is related to the seed word '{seed_word}' with {difficulty} difficulty. 
        For each user guess, respond ONLY with a JSON object containing: 
        1. 'percentage' (0-100 number estimating similarity to target)
        2. 'hint' (a helpful but not overly obvious clue that:
            - Points the user in the right direction
            - References their guess and how it relates to the target
            - Provides meaningful context about the target word
            - Avoids being too direct or revealing)
        Example: {{"percentage": 75, "hint": "Your guess 'fruit' is close - the target is also something that grows on trees, but it's specifically a type of citrus"}}
        Do NOT include any other text or formatting."""
    }
    
    return jsonify({
        "status": "success",
        "message": f"Game started with seed: {seed_word}, difficulty: {difficulty}"
    })

SYSTEM_MESSAGE = {
    "role": "system",
    "content": f"""You are a word guessing game master. The target word is '{TARGET_WORD}'. 
    For each user guess, respond ONLY with a JSON object containing: 
    1. 'percentage' (0-100 number estimating similarity to target)
    2. 'hint' (a helpful but not overly obvious clue that:
        - Points the user in the right direction
        - References their guess and how it relates to the target
        - Provides meaningful context about the target word
        - Avoids being too direct or revealing)
    Example: {{"percentage": 75, "hint": "Your guess 'fruit' is close - the target is also something that grows on trees, but it's specifically a type of citrus"}}
    Do NOT include any other text or formatting."""
}

@app.route('/give-up', methods=['POST'])
def give_up():
    global TARGET_WORD, SYSTEM_MESSAGE
    # Get current target word
    current_word = TARGET_WORD
    # Get new target word
    TARGET_WORD = get_target_word()
    # Update system message with new target word
    SYSTEM_MESSAGE = {
        "role": "system",
                "content": f"""You are a word guessing game master. The target word is '{TARGET_WORD}'. 
                For each user guess, respond ONLY with a JSON object containing: 
                1. 'percentage' (0-100 number estimating similarity to target)
                2. 'hint' (a helpful but not overly obvious clue that:
                    - Points the user in the right direction
                    - References their guess and how it relates to the target
                    - Provides meaningful context about the target word
                    - Avoids being too direct or revealing)
                Example: {{"percentage": 75, "hint": "Your guess 'fruit' is close - the target is also something that grows on trees, but it's specifically a type of citrus"}}
                Do NOT include any other text or formatting."""
    }
    return jsonify({
        "old_word": current_word,
        "new_word": TARGET_WORD,
        "message": f"The word was: {current_word}. New word selected!"
    })

@app.route('/chat', methods=['POST'])
def chat():
    global TARGET_WORD, SYSTEM_MESSAGE
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
            response_data = json.loads(llm_response)
            # Check if guess was correct (100% similarity)
            if response_data.get('percentage', 0) == 100:
                # Get new target word
                TARGET_WORD = get_target_word()
                # Update system message with new target word
                SYSTEM_MESSAGE = {
                    "role": "system",
                    "content": f"""You are a word guessing game master. The target word is '{TARGET_WORD}'. 
                    For each user guess, respond ONLY with a JSON object containing: 
                    1. 'percentage' (0-100 number estimating similarity to target)
                    2. 'hint' (a helpful but not overly obvious clue that:
                        - Points the user in the right direction
                        - References their guess and how it relates to the target
                        - Provides meaningful context about the target word
                        - Avoids being too direct or revealing)
                    Example: {{"percentage": 75, "hint": "Your guess 'fruit' is close - the target is also something that grows on trees, but it's specifically a type of citrus"}}
                    Do NOT include any other text or formatting."""
                }
                # Add success message to response
                response_data['success'] = f"Correct! New word selected. Keep guessing!"
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid response format from AI"}), 500

        return jsonify({"content": json.dumps(response_data)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
