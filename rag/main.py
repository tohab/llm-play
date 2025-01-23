# app.py
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings

# Custom embedding class for Deepseek
class DeepseekEmbeddings(Embeddings):
    def __init__(self, client):
        self.client = client
        
    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]
    
    def embed_query(self, text):
        response = self.client.embeddings.create(
            input=text,
            model="text-embedding-002"  # Verify correct model name with Deepseek docs
        )
        return response.data[0].embedding

# Initialize application
load_dotenv()
app = Flask(__name__)
CORS(app)

# Initialize Deepseek client
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# Load and process The Art of War text
loader = TextLoader("art_of_war.txt")
documents = loader.load()

# Split text into chunks
text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
texts = text_splitter.split_documents(documents)

# Create vector store with Deepseek embeddings
embeddings = DeepseekEmbeddings(client)
vector_store = FAISS.from_documents(texts, embeddings)

# System prompt template
SYSTEM_TEMPLATE = """You are Sun Tzu's digital incarnation. Respond to questions using wisdom from The Art of War. 
Consider these relevant passages:
{context}

Always include direct quotes from the text when appropriate. Structure your response like Sun Tzu would speak."""

# Chat endpoint
@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        messages = data.get('messages', [])
        
        if not messages:
            return jsonify({"error": "No messages provided"}), 400
            
        # Extract latest user message
        user_message = messages[-1]["content"]
        
        # Retrieve relevant context
        docs = vector_store.similarity_search(user_message, k=3)
        context = "\n\n".join([d.page_content for d in docs])
        
        # Prepare system message with context
        system_message = SYSTEM_TEMPLATE.format(context=context)
        
        # Construct message history
        chat_messages = [
            {"role": "system", "content": system_message},
            *messages
        ]

        # Generate streaming response
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=chat_messages,
            stream=True
        )

        def generate():
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield json.dumps({"content": chunk.choices[0].delta.content})

        return Response(generate(), mimetype="application/json")

    except Exception as e:
        app.logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({"error": "An error occurred processing your request"}), 500

if __name__ == '__main__':
    app.run(debug=True)