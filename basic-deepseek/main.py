from flask import Flask, request, jsonify, Response  # Update Response import
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os
import json

load_dotenv()  # Load environment variables

app = Flask(__name__)
CORS(app)

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),  # Get from .env
    base_url="https://api.deepseek.com"
)

SYSTEM_MESSAGE = {
    "role": "system",
    "content": "You are a helpful AI assistant. Respond helpfully, think critically, and ask for further instructions whenever necessary."
}

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    messages = data.get('messages', [])

    # Filter out existing system messages and prepend ours
    filtered_messages = [msg for msg in messages if msg.get("role") != "system"]
    messages_with_system = [SYSTEM_MESSAGE] + filtered_messages

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages_with_system,
            stream=True  # Enable streaming
        )

        def generate():
            for chunk in response:
                if content := chunk.choices[0].delta.content:
                    yield json.dumps({"content": content})

        return Response(generate(), mimetype="application/json")

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)