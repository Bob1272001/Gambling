from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

app = FastAPI()

# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve the HTML file


@app.get("/", response_class=HTMLResponse)
async def read_index():
    # Path to the HTML file in the static directory
    html_path = os.path.join("static", "index.html")
    return FileResponse(html_path)


# API endpoint
@app.get("/api/hello")
async def say_hello():
    return {"message": "Hello from FastAPI!"}
