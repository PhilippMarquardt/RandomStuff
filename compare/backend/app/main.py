from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.v1 import chat as chat_v1
from api.v1 import upload as upload_v1
from api.v1 import convert as convert_v1
from api.v1 import pdf_words as pdf_words_v1
from api.v1 import templates as templates_v1
from api.v1 import data as data_v1

app = FastAPI(title="LLM Chat Backend", version="0.1.0")

# CORS settings
origins = [
    "http://localhost:3000",  # Next.js default dev port
    # Add any other origins if needed (e.g., your production frontend URL)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_v1.router, prefix="/api/v1/chat", tags=["Chat V1"])
app.include_router(upload_v1.router, prefix="/api/v1/upload", tags=["Upload V1"])
app.include_router(convert_v1.router, prefix="/api/v1/convert", tags=["Convert V1"])
app.include_router(pdf_words_v1.router, prefix="/api/v1/pdf", tags=["PDF Words V1"])
app.include_router(templates_v1.router, prefix="/api/v1/templates", tags=["Templates V1"])
app.include_router(data_v1.router, prefix="/api/v1/data", tags=["Data Files"])

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "ok"} 