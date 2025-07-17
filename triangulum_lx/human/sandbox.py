"""
Sandbox for file and folder processing.

This module provides a mechanism for users to upload files or folders,
have them processed in an isolated environment, and then download the
results.
"""

import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from starlette.responses import FileResponse

app = FastAPI()

# A simple in-memory database to track sandbox environments
sandboxes: Dict[str, Dict[str, Any]] = {}


import zipfile

SANDBOX_DIR = Path("sandbox_environments")
SANDBOX_DIR.mkdir(exist_ok=True)

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file or a zip archive of a folder to a new sandbox.
    """
    sandbox_id = str(uuid.uuid4())
    sandbox_path = SANDBOX_DIR / sandbox_id
    sandbox_path.mkdir()

    file_path = sandbox_path / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    if file.filename.endswith(".zip"):
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(sandbox_path)
        os.remove(file_path)

    sandboxes[sandbox_id] = {
        "id": sandbox_id,
        "path": str(sandbox_path),
        "original_filename": file.filename,
        "processed": False,
    }

    return {"sandbox_id": sandbox_id, "message": "File uploaded successfully."}


@app.post("/process/{sandbox_id}/")
async def process_file(sandbox_id: str):
    """
    Process the file in the sandbox.
    """
    if sandbox_id not in sandboxes:
        raise HTTPException(status_code=404, detail="Sandbox not found.")

    sandbox_path = Path(sandboxes[sandbox_id]["path"])

    for item in sandbox_path.iterdir():
        if item.is_file():
            processed_file_path = item.with_name(f"{item.name}_processed")
            shutil.copy(item, processed_file_path)

    sandboxes[sandbox_id]["processed"] = True

    return {"sandbox_id": sandbox_id, "message": "File processed successfully."}


@app.get("/list/{sandbox_id}/")
async def list_files(sandbox_id: str):
    """
    List the files in the sandbox.
    """
    if sandbox_id not in sandboxes:
        raise HTTPException(status_code=404, detail="Sandbox not found.")

    sandbox_path = Path(sandboxes[sandbox_id]["path"])
    files = [f.name for f in sandbox_path.iterdir() if f.is_file()]

    return {"sandbox_id": sandbox_id, "files": files}


@app.get("/download/{sandbox_id}/")
async def download_file(sandbox_id: str, filename: str):
    """
    Download a file from the sandbox.
    """
    if sandbox_id not in sandboxes:
        raise HTTPException(status_code=404, detail="Sandbox not found.")

    sandbox_path = Path(sandboxes[sandbox_id]["path"])
    file_path = sandbox_path / filename

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found in sandbox.")

    return FileResponse(file_path, filename=filename)


@app.post("/overwrite/{sandbox_id}/")
async def overwrite_file(sandbox_id: str, filename: str, original_path: str = Form(...)):
    """
    Overwrite the original file with the processed version.
    """
    if sandbox_id not in sandboxes:
        raise HTTPException(status_code=404, detail="Sandbox not found.")

    sandbox_path = Path(sandboxes[sandbox_id]["path"])
    processed_file_path = sandbox_path / filename
    original_path = Path(original_path)

    if not processed_file_path.is_file():
        raise HTTPException(status_code=404, detail="Processed file not found in sandbox.")

    # For security, we should probably add some checks here to ensure that the
    # user is not overwriting a system file. For now, we'll just trust the user.

    shutil.copyfile(processed_file_path, original_path)

    return {"message": f"File '{original_path}' overwritten successfully."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
