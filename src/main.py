from fastapi import FastAPI
# Import specific module's router
from rf_intelligence.routes import router as rf_router

# Initialize the main FastAPI application
app = FastAPI(
    title="Intelligent Counter-UAS PoC Simulator",
    description="Software-based simulator for hostile drone detection and response."
)

# Include your RF module's router
app.include_router(rf_router)

# A simple health-check for the main server
@app.get("/")
def read_root():
    return {"status": "online", "message": "Counter-UAS Simulator Core is running."}