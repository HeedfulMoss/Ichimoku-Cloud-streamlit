from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import tickers

app = FastAPI(title="Ichimoku Cloud API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tickers.router, prefix="/api", tags=["tickers"])

@app.get("/")
async def root():
    return {"message": "Welcome to Ichimoku Cloud API"}