# Main entry point for the FastAPI application
# This file imports and runs the app from app.main

from app.main import app

# For uvicorn to find the app when running `uvicorn main:app`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
