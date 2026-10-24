"""
Root entrypoint for running the backend with `python main.py` or `uvicorn main:app`.
"""

import os
import uvicorn
from app.main import app
from app.config import settings

if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.PORT))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
