from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import aoi, job, results

app = FastAPI(
    title="SAR + MS Tarımsal Hasar Analizi API",
    description="Tarımsal Hasar Analizi için FastAPI tabanlı backend",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(aoi.router, prefix="/api/v1/aoi", tags=["aoi"])
app.include_router(job.router, prefix="/api/v1")
app.include_router(results.router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {"message": "Tarımsal Hasar Analizi API Çalışıyor"}
