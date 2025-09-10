"""
Model Registry - Clean and simple model management
Register and initialize different LangChain models
"""
import os
from typing import Dict, Type, TypeVar, Generic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

# Ensure API key is available
if not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "your_openai_api_key_here"

T = TypeVar("T")

class ModelRegistry(Generic[T]):
    def __init__(self):
        self._models: Dict[str, Type[T]] = {}

    def register(self, name: str):
        def decorator(cls: Type[T]):
            self._models[name] = cls
            return cls
        return decorator

    def get_model(self, name: str, **kwargs) -> T:
        model_cls = self._models.get(name)
        if not model_cls:
            raise ValueError(f"Model '{name}' not found.")
        return model_cls(**kwargs)

    def get_available_models(self):
        return list(self._models.keys())

# Create registry instance for chat models
chat_model_registry = ModelRegistry[BaseChatModel]()


@chat_model_registry.register("gpt-5-mini")
class ChatOpenAI4oMini(ChatOpenAI):
    def __init__(self, **kwargs):
        super().__init__(
            model="gpt-5-mini", 
            api_key=os.getenv("OPENAI_API_KEY"),
            max_tokens=2000,
            **kwargs
        )


# Export the registry
model_registry = chat_model_registry
