import os
import sys
from pathlib import Path

# Ensure src is on Python search path
ROOT = Path(__file__).resolve().parent
src_path = str(ROOT / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import uvicorn
from docextract.api.main import app

# Hugging Face Spaces can run FastAPI directly as ASGI `app`
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)

