from fastapi import FastAPI

app = FastAPI(title="Sector Strength API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Sector Strength API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}