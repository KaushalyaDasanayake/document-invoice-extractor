import os
import sys
from pathlib import Path

# Ensure src is on Python search path
ROOT = Path(__file__).resolve().parent
src_path = str(ROOT / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import gradio as gr
from docextract.api.main import app as fastapi_app

# Mount our full FastAPI app and UI directly into Gradio
# This satisfies Gradio Space lifecycle checks while serving our studio and API
app = gr.mount_gradio_app(fastapi_app, gr.Blocks(), path="/gradio")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("app:app", host="0.0.0.0", port=port)


