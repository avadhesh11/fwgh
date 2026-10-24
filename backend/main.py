"""
Root entrypoint for running the backend with `python main.py` or `uvicorn main:app`.
"""

import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
