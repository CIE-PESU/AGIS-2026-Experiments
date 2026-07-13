import json
import os
import sys

# Add backend directory to sys.path so app can be imported properly
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app

def main():
    openapi_schema = app.openapi()
    
    # Workspace root is two levels up from scripts directory
    workspace_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    output_path = os.path.join(workspace_root, "docs", "api-spec-generated.json")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"Exported OpenAPI schema to {output_path}")

if __name__ == "__main__":
    main()
