import pytest
from fastapi.testclient import TestClient
from triangulum_lx.human.sandbox import app
import os
import shutil
from pathlib import Path
import zipfile

client = TestClient(app)

@pytest.fixture(scope="module")
def test_data():
    """Creates a dummy file for testing uploads."""
    test_dir = Path("test_sandbox_data")
    test_dir.mkdir(exist_ok=True)
    file_path = test_dir / "test_file.txt"
    with open(file_path, "w") as f:
        f.write("This is a test file.")

    zip_path = test_dir / "test_archive.zip"
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.write(file_path, arcname=file_path.name)

    yield {"dir": test_dir, "file": file_path, "zip": zip_path}
    shutil.rmtree(test_dir)

def test_upload_file(test_data):
    """Tests the /upload/ endpoint with a single file."""
    with open(test_data["file"], "rb") as f:
        response = client.post("/upload/", files={"file": ("test_file.txt", f, "text/plain")})
    assert response.status_code == 200
    data = response.json()
    assert "sandbox_id" in data
    assert "message" in data
    assert data["message"] == "File uploaded successfully."

def test_upload_zip(test_data):
    """Tests the /upload/ endpoint with a zip archive."""
    with open(test_data["zip"], "rb") as f:
        response = client.post("/upload/", files={"file": ("test_archive.zip", f, "application/zip")})
    assert response.status_code == 200
    data = response.json()
    assert "sandbox_id" in data
    assert "message" in data
    assert data["message"] == "File uploaded successfully."

    # Verify that the zip file was extracted
    sandbox_id = data["sandbox_id"]
    response = client.get(f"/list/{sandbox_id}/")
    assert response.status_code == 200
    assert "test_file.txt" in response.json()["files"]


def test_process_file(test_data):
    """Tests the /process/{sandbox_id}/ endpoint."""
    with open(test_data["file"], "rb") as f:
        response = client.post("/upload/", files={"file": ("test_file.txt", f, "text/plain")})
    sandbox_id = response.json()["sandbox_id"]
    response = client.post(f"/process/{sandbox_id}/")
    assert response.status_code == 200
    data = response.json()
    assert data["sandbox_id"] == sandbox_id
    assert data["message"] == "File processed successfully."

    # Verify that the processed file was created
    response = client.get(f"/list/{sandbox_id}/")
    assert response.status_code == 200
    assert "test_file.txt_processed" in response.json()["files"]


def test_list_files(test_data):
    """Tests the /list/{sandbox_id}/ endpoint."""
    with open(test_data["file"], "rb") as f:
        response = client.post("/upload/", files={"file": ("test_file.txt", f, "text/plain")})
    sandbox_id = response.json()["sandbox_id"]
    response = client.get(f"/list/{sandbox_id}/")
    assert response.status_code == 200
    data = response.json()
    assert data["sandbox_id"] == sandbox_id
    assert "files" in data
    assert "test_file.txt" in data["files"]


def test_download_file(test_data):
    """Tests the /download/{sandbox_id}/ endpoint."""
    with open(test_data["file"], "rb") as f:
        response = client.post("/upload/", files={"file": ("test_file.txt", f, "text/plain")})
    sandbox_id = response.json()["sandbox_id"]
    response = client.get(f"/download/{sandbox_id}/?filename=test_file.txt")
    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="test_file.txt"'
    with open(test_data["file"], "rb") as f:
        assert response.content == f.read()

def test_overwrite_file(test_data):
    """Tests the /overwrite/{sandbox_id}/ endpoint."""
    with open(test_data["file"], "rb") as f:
        response = client.post("/upload/", files={"file": ("test_file.txt", f, "text/plain")})
    sandbox_id = response.json()["sandbox_id"]

    # Create a dummy original file to be overwritten
    original_file_path = test_data["dir"] / "original_file.txt"
    with open(original_file_path, "w") as f:
        f.write("This is the original file.")

    response = client.post(f"/overwrite/{sandbox_id}/?filename=test_file.txt", data={"original_path": str(original_file_path)})
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == f"File '{original_file_path}' overwritten successfully."

    # Verify that the original file was overwritten
    with open(original_file_path, "r") as f:
        assert f.read() == "This is a test file."
