"""
LLM Provider abstraction for easy switching between different language models.
Configure via environment variables:

OpenAI:
- LLM_PROVIDER=openai
- OPENAI_API_KEY=your_key
- LLM_MODEL=gpt-4-turbo-preview (optional, default)

Anthropic:
- LLM_PROVIDER=anthropic
- ANTHROPIC_API_KEY=your_key
- LLM_MODEL=claude-3-opus-20240229 (optional, default)

Local/Ollama:
- LLM_PROVIDER=ollama
- OLLAMA_BASE_URL=http://localhost:11434 (optional, default)
- LLM_MODEL=llama2 (required for ollama)
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class LLMProvider(ABC):
    @abstractmethod
    def generate_response(self, messages: list, max_tokens: int = 1500, temperature: float = 0.1) -> str:
        """Generate a response from the LLM given a list of messages."""
        pass

class OpenAIProvider(LLMProvider):
    def __init__(self, model: str = "gpt-4-turbo-preview"):
        import openai
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    def generate_response(self, messages: list, max_tokens: int = 1500, temperature: float = 0.1) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content

class AnthropicProvider(LLMProvider):
    def __init__(self, model: str = "claude-3-opus-20240229"):
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            self.model = model
        except ImportError:
            raise ImportError("Please install anthropic: pip install anthropic")

    def generate_response(self, messages: list, max_tokens: int = 1500, temperature: float = 0.1) -> str:
        # Convert OpenAI format to Anthropic format
        system_message = ""
        user_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                user_messages.append(msg)
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_message,
            messages=user_messages
        )
        return response.content[0].text

class OllamaProvider(LLMProvider):
    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        try:
            import requests
            self.base_url = base_url.rstrip('/')
            self.model = model
            self.session = requests.Session()
        except ImportError:
            raise ImportError("Please install requests: pip install requests")

    def generate_response(self, messages: list, max_tokens: int = 1500, temperature: float = 0.1) -> str:
        # Convert to Ollama format
        prompt = ""
        for msg in messages:
            if msg["role"] == "system":
                prompt += f"System: {msg['content']}\n\n"
            elif msg["role"] == "user":
                prompt += f"User: {msg['content']}\n\n"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        response = self.session.post(f"{self.base_url}/api/generate", json=payload)
        response.raise_for_status()
        return response.json()["response"]

def get_llm_provider() -> LLMProvider:
    """
    Factory function to get the configured LLM provider based on environment variables.
    """
    provider_name = os.getenv("LLM_PROVIDER", "openai").lower()
    model = os.getenv("LLM_MODEL")
    
    if provider_name == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY must be set when using OpenAI provider")
        return OpenAIProvider(model or "gpt-4-turbo-preview")
    
    elif provider_name == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY must be set when using Anthropic provider")
        return AnthropicProvider(model or "claude-3-opus-20240229")
    
    elif provider_name == "ollama":
        if not model:
            raise ValueError("LLM_MODEL must be set when using Ollama provider")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return OllamaProvider(model, base_url)
    
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_name}. Supported: openai, anthropic, ollama") 