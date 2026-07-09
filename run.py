import uvicorn
import os

if __name__ == "__main__":
    # This script allows you to start the Dark Swarm Factory from the root directory.
    # It will automatically serve the frontend from the backend/main.py configuration.
    print("🚀 Starting Dark Swarm Factory...")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
