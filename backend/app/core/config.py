from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    OPENAI_API_KEY: str = 

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings() 