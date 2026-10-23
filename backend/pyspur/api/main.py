# Originally from PySpur (https://github.com/PySpur-Dev/pyspur), licensed under Apache-2.0.
# Modified by Alokin LLC, 2026; modifications licensed under FCL-1.0-ALv2.
# SPDX-License-Identifier: Apache-2.0 AND FCL-1.0-ALv2
import os
import shutil
import tempfile
import threading
from contextlib import ExitStack, asynccontextmanager
from importlib.resources import as_file, files
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from .api_app import api_app

load_dotenv()

# Create an ExitStack to manage resources
exit_stack = ExitStack()
temporary_static_dir = None
socket_manager = None
socket_thread = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan and cleanup."""
    global temporary_static_dir, socket_manager, socket_thread

    # Setup: Create temporary directory and extract static files
    temporary_static_dir = Path(tempfile.mkdtemp())

    # Extract static files to temporary directory
    static_files = files("pyspur").joinpath("static")
    static_dir = exit_stack.enter_context(as_file(static_files))

    # Copy static files to temporary directory
    if static_dir.exists():
        shutil.copytree(static_dir, temporary_static_dir, dirs_exist_ok=True)


    yield

    # Cleanup: Stop socket manager and remove temporary directory
    if socket_manager:
        logger.info("Stopping socket manager...")
        socket_manager.stopping = True
        if socket_thread and socket_thread.is_alive():
            try:
                # Give the thread a chance to stop gracefully
                socket_thread.join(timeout=5)
            except Exception as e:
                logger.error(f"Error stopping socket manager thread: {e}")

    exit_stack.close()
    shutil.rmtree(temporary_static_dir, ignore_errors=True)


app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PYSPUR_API_KEY = os.environ.get("PYSPUR_API_KEY")


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    if not request.url.path.startswith("/api/"):
        return await call_next(request)
    if request.url.path == "/api/health":
        # Health checks must work without the API key.
        return await call_next(request)
    if not PYSPUR_API_KEY:
        return await call_next(request)
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth[7:] != PYSPUR_API_KEY:
        return JSONResponse({"detail": "Invalid or missing Authorization header"}, status_code=401)
    return await call_next(request)


# Registered before the /api mount below, so /api/health is answered here.
@app.get("/health", include_in_schema=False)
@app.get("/api/health", include_in_schema=False)
async def health_check():
    return {"status": "ok"}


# Mount the API routes under /api
app.mount("/api", api_app, name="api")

# Optionally, mount directories for assets that you want served directly:
if temporary_static_dir and Path.joinpath(temporary_static_dir, "images").exists():
    app.mount(
        "/images",
        StaticFiles(directory=str(temporary_static_dir.joinpath("images"))),
        name="images",
    )
if temporary_static_dir and Path.joinpath(temporary_static_dir, "_app").exists():
    app.mount(
        "/_app", StaticFiles(directory=str(temporary_static_dir.joinpath("_app"))), name="_app"
    )


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    if not temporary_static_dir:
        raise RuntimeError("Static directory not initialized")

    # SvelteKit adapter-static SPA fallback file
    spa_fallback = temporary_static_dir.joinpath("200.html")

    # If the request is empty, serve the SPA fallback
    if full_path == "":
        return FileResponse(spa_fallback)

    # remove trailing slash
    if full_path[-1] == "/":
        full_path = full_path[:-1]

    # Build a candidate file path from the request.
    candidate = temporary_static_dir.joinpath(full_path)

    # If candidate is a directory, try its index.html.
    if candidate.is_dir():
        candidate_index = candidate.joinpath("index.html")
        if candidate_index.exists():
            return FileResponse(candidate_index)

    # If no direct file, try appending ".html"
    candidate_html = temporary_static_dir.joinpath(full_path + ".html")
    if candidate_html.exists():
        return FileResponse(candidate_html)

    # If a file exists at that candidate, serve it.
    if candidate.exists():
        return FileResponse(candidate)

    # Check if the parent directory contains a file named "[id].html"
    parts = full_path.split("/")
    if len(parts) >= 2:
        parent = temporary_static_dir.joinpath(*parts[:-1])
        dynamic_file = parent.joinpath("[id].html")
        if dynamic_file.exists():
            return FileResponse(dynamic_file)

    # Fallback: serve the SvelteKit SPA fallback for client-side routing.
    return FileResponse(spa_fallback)
