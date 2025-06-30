import os
from typing import Dict, Type, TypeVar, Generic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


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

# Create registry instances for different model types
chat_model_registry = ModelRegistry[BaseChatModel]()
embedding_model_registry = ModelRegistry[Embeddings]()


@chat_model_registry.register("gpt-4o-mini")
class ChatOpenAI4oMini(ChatOpenAI):
    def __init__(self, **kwargs):
        super().__init__(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"), **kwargs)

@embedding_model_registry.register("text-embedding-3-large")
class TextEmbedding3Large(OpenAIEmbeddings):
    def __init__(self, **kwargs):
        super().__init__(model="text-embedding-3-large", api_key=os.getenv("OPENAI_API_KEY"), **kwargs) 