import os
os.environ["OPENAI_API_KEY"] = 
from typing import Dict, Type
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

class ModelRegistry:
    def __init__(self):
        self._models: Dict[str, Type[BaseChatModel]] = {}

    def register(self, name: str):
        def decorator(cls: Type[BaseChatModel]):
            self._models[name] = cls
            return cls
        return decorator

    def get_model(self, name: str, **kwargs) -> BaseChatModel:
        model_cls = self._models.get(name)
        if not model_cls:
            raise ValueError(f"Model '{name}' not found.")
        return model_cls(**kwargs)

    def get_available_models(self):
        return list(self._models.keys())

# Create a single registry instance
model_registry = ModelRegistry()


@model_registry.register("gpt-4o-mini")
class ChatOpenAI4(ChatOpenAI):
    def __init__(self, **kwargs):
        super().__init__(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"), **kwargs) 