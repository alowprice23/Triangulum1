import os
import sys
import importlib
from pathlib import Path

def main():
    """
    Smoke test to ensure all Python modules within the triangulum_lx package
    can be imported without raising immediate errors like ModuleNotFoundError
    or SyntaxError. This is a basic structural integrity check.
    """
    project_root = Path(__file__).parent.parent
    package_path = project_root / 'triangulum_lx'

    # Add project root to sys.path to allow for absolute imports
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    print(f"Starting import smoke test for package: {package_path}")

    success_count = 0
    fail_count = 0

    # Walk through all files in the package directory
    for root, _, files in os.walk(package_path):
        for file in files:
            if file.endswith('.py'):
                # Construct the module path from the file path
                relative_path = Path(root).relative_to(project_root)
                module_name_parts = list(relative_path.parts)

                if file == '__init__.py':
                    # This is a package/subpackage
                    module_name = ".".join(module_name_parts)
                else:
                    # This is a module
                    module_name_parts.append(Path(file).stem)
                    module_name = ".".join(module_name_parts)

                # Skip the smoke test script itself if it's somehow in the path
                if "scripts.smoke_test_imports" in module_name:
                    continue

                try:
                    print(f"Attempting to import: {module_name}", end=' ... ')
                    importlib.import_module(module_name)
                    print("SUCCESS")
                    success_count += 1
                except Exception as e:
                    print(f"FAILED\n  -> Error: {e.__class__.__name__}: {e}")
                    fail_count += 1

    print("\n--- Smoke Test Summary ---")
    print(f"Successful imports: {success_count}")
    print(f"Failed imports: {fail_count}")

    if fail_count > 0:
        print("\nSmoke test FAILED. Please fix the above import errors.")
        sys.exit(1)
    else:
        print("\nSmoke test PASSED. Basic structure appears sound.")
        sys.exit(0)

if __name__ == "__main__":
    main()
