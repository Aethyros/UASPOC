from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import specific module's router
from rf_intelligence.routes import router as rf_router

# Initialize the main FastAPI application
app = FastAPI(
    title="Intelligent Counter-UAS PoC Simulator",
    description="Software-based simulator for hostile drone detection and response."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows any local port to connect during parallel development
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, etc.
    allow_headers=["*"],
)

# Register routes with the main application
app.include_router(rf_router)

# A simple health-check route for the main server
@app.get("/")
def read_root():
    return {
        "status": "online", 
        "module": "RF Detection & Signal Intelligence",
        "message": "Counter-UAS Simulator Core is running. Visit /docs for the API Swagger UI."
    }