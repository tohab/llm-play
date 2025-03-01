import os
from openai import OpenAI
from typing import Generator

class LLMHandler:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )
        self.command_prefixes = ['/help', '/save', '/list']
        self.system_message = {
            "role": "system",
            "content": """You are a helpful AI assistant that helps users manage their notes. 
            Your responsibilities include:
            - Determining if the user wants to save a note or list their notes
            - Helping users organize their thoughts
            - Responding helpfully to general questions
            
            When the user wants to save a note, extract just the note content without any additional commentary."""
        }

    def generate_response(self, prompt: str, stream: bool = False) -> str | Generator:
        """Generate response using LLM
        
        Args:
            prompt: User input prompt
            stream: Whether to stream the response
            
        Returns:
            str or Generator: Complete response or streaming generator
        """
        try:
            messages = [
                self.system_message,
                {"role": "user", "content": prompt}
            ]
            
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                stream=stream
            )
            
            if stream:
                def generate():
                    for chunk in response:
                        if content := chunk.choices[0].delta.content:
                            yield content
                return generate()
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error generating response: {str(e)}"
