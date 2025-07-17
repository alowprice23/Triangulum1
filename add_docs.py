import os

# The definitive executable route to start the application
DOCS_HEADER = """
# This file is part of the Triangulum project.
#
# To start the application, run the following command:
#
# tsh --help
#
"""

# List of files and directories to include
INCLUDE_LIST = [
    "triangulum_lx",
    "triangulum",
    "AGENT_COLLABORATION_PROTOCOL.md",
    "cla.sh",
    "create_project.sh",
    "docker-compose.yml",
    "Makefile",
    "pyproject.toml",
    "pytest.ini",
    "README.md",
    "requirements.in",
    "requirements.txt",
    "setup.cfg",
    "setup.py",
]

# List of file extensions to include
INCLUDE_EXTENSIONS = [
    ".py",
    ".md",
    ".sh",
    ".yml",
    ".yaml",
    ".cfg",
    ".toml",
    ".txt"
]

def should_include(path):
    """Check if a file or directory should be included."""
    for item in INCLUDE_LIST:
        if item in path:
            return True
    return False

def add_docs_to_file(filepath):
    """Add the documentation header to a file."""
    if not should_include(filepath):
        return

    # Check if the file extension is in the include list
    if not any(filepath.endswith(ext) for ext in INCLUDE_EXTENSIONS):
        return

    try:
        with open(filepath, "r+") as f:
            content = f.read()
            if not content.startswith(DOCS_HEADER.strip()):
                f.seek(0, 0)
                f.write(DOCS_HEADER.strip() + "\n\n" + content)
                print(f"Added docs to {filepath}")
    except Exception as e:
        print(f"Could not process {filepath}: {e}")

def main():
    """Main function to add docs to all files."""
    for root, dirs, files in os.walk("."):
        # Exclude directories that are not in the include list
        dirs[:] = [d for d in dirs if should_include(os.path.join(root, d))]

        for file in files:
            filepath = os.path.join(root, file)
            if should_include(filepath):
                add_docs_to_file(filepath)

if __name__ == "__main__":
    main()
