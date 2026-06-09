"""
LLM Client Module

Unified interface for LLM providers using OpenRouter API.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import json
import requests
import os

# OpenRouter API Configuration
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY",
    "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"
)
DEFAULT_MODEL = "openai/gpt-4o-mini"
DEFAULT_MAX_TOKENS = 1000
DEFAULT_TEMPERATURE = 0.7


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate a JSON response from the LLM."""
        pass


class OpenRouterClient(BaseLLMClient):
    """OpenRouter API client for accessing various LLMs."""
    
    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        max_tokens: int = None,
        temperature: float = None
    ):
        """
        Initialize OpenRouter client.
        
        Args:
            api_key: OpenRouter API key
            model: Model identifier (default: openai/gpt-4o-mini)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
        """
        self.api_key = api_key or OPENROUTER_API_KEY
        self.model = model or DEFAULT_MODEL
        self.max_tokens = max_tokens or DEFAULT_MAX_TOKENS
        self.temperature = temperature or DEFAULT_TEMPERATURE
        self.api_url = OPENROUTER_API_URL
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def generate(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        """
        Generate a text response.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system instructions
            **kwargs: Additional parameters (model, max_tokens, temperature)
            
        Returns:
            Generated text response
        """
        default_system = "You are an expert data analyst and statistician. Your goal is to explain statistical results clearly, provide actionable real-world insights, and diagnose potential issues in the data."
        
        data = {
            "model": kwargs.get('model', self.model),
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt or default_system
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": kwargs.get('max_tokens', self.max_tokens),
            "temperature": kwargs.get('temperature', self.temperature)
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=self._get_headers(),
                json=data,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
            
            return ""
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"OpenRouter API error: {e}")
    
    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generate a JSON response.
        
        Args:
            prompt: User prompt (should request JSON output)
            **kwargs: Additional parameters
            
        Returns:
            Parsed JSON response
        """
        # Add JSON instruction to prompt
        json_prompt = prompt + "\n\nIMPORTANT: Respond with valid JSON only, no other text or markdown formatting."
        
        content = self.generate(json_prompt, **kwargs)
        
        # Try to parse JSON from response
        try:
            # Clean up potential markdown code blocks
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            return json.loads(content)
            
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            import re
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            # Return a default structure if parsing fails
            return {"error": "Failed to parse JSON", "raw_response": content}


class MockLLMClient(BaseLLMClient):
    """Mock client for testing without API calls."""
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Return a mock response."""
        return "This is a mock response for testing purposes. The original concept involves academic discussion."
    
    def generate_json(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Return a mock JSON response."""
        if "idea" in prompt.lower() or "extract" in prompt.lower():
            return {
                "ideas": [
                    {"concept": "Main concept from the sentence", "importance": "primary"},
                    {"concept": "Supporting concept", "importance": "secondary"}
                ],
                "main_topic": "Academic research topic",
                "logical_relationships": ["cause-effect", "comparison"]
            }
        elif "perspective" in prompt.lower():
            return {
                "recommended_perspectives": [
                    {"type": "OBSERVATION", "suitability": 0.9, "reason": "Good for empirical findings"},
                    {"type": "CAUSE_EFFECT", "suitability": 0.7, "reason": "Shows relationships"}
                ]
            }
        elif "generate" in prompt.lower() or "sentence" in prompt.lower():
            return {
                "sentence": "Research findings demonstrate that the phenomenon exhibits significant characteristics.",
                "confidence": 0.85,
                "changes_made": ["Changed sentence structure", "Used different vocabulary"]
            }
        return {"mock": True, "response": "Mock JSON response"}


class LLMClient:
    """Factory class for LLM clients."""
    
    _instance: Optional[BaseLLMClient] = None
    
    @classmethod
    def get_client(cls, provider: str = None) -> BaseLLMClient:
        """
        Get an LLM client instance.
        
        Args:
            provider: Provider name (openrouter, mock)
            
        Returns:
            LLM client instance
        """
        provider = provider or "openrouter"
        
        if provider in ("openrouter", "openai", "default"):
            return OpenRouterClient()
        elif provider == "mock":
            return MockLLMClient()
        else:
            # Default to OpenRouter
            return OpenRouterClient()
    
    @classmethod
    def get_default(cls) -> BaseLLMClient:
        """Get the default LLM client (singleton)."""
        if cls._instance is None:
            cls._instance = cls.get_client("openrouter")
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Reset the singleton instance."""
        cls._instance = None


# Convenience function for quick testing
def test_connection() -> bool:
    """Test the OpenRouter API connection."""
    try:
        client = OpenRouterClient()
        response = client.generate("Say 'API connection successful' in exactly those words.")
        print(f"API Test Response: {response}")
        return "successful" in response.lower() or len(response) > 0
    except Exception as e:
        print(f"API Test Failed: {e}")
        return False


if __name__ == "__main__":
    # Quick test
    test_connection()
