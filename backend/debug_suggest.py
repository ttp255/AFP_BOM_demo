import os
import traceback
from dotenv import load_dotenv

# Load real environment variables from backend/.env
load_dotenv()

# Explicitly ensure mock DB is false to test real connection
os.environ["AFP_USE_MOCK_DB"] = "false"

from app.db.supabase_client import supabase
from app.services.pipeline_service import suggest_products_for_project

def main():
    print("Connecting to Supabase at:", os.getenv("SUPABASE_URL"))
    try:
        projects = supabase.table("afp_projects").select("*").execute().data
        print(f"Found {len(projects)} projects.")
        for p in projects:
            print(f"- ID: {p['id']}, Code: {p['project_code']}, Name: {p['project_name']}, Status: {p['status']}")
            
            # Let's check BOM items count for this project
            bom_items = supabase.table("afp_bom_items").select("*").eq("project_id", p["id"]).execute().data
            print(f"  BOM items count: {len(bom_items)}")
            
            if len(bom_items) > 0:
                print("  Attempting to run suggest_products_for_project...")
                try:
                    suggestions = suggest_products_for_project(p["id"], enrich_with_ai=False)
                    print(f"  Success! Generated {len(suggestions)} suggestions (enrich_with_ai=False)")
                except Exception as e:
                    print("  Failed with error:")
                    traceback.print_exc()
    except Exception as e:
        print("General failure:")
        traceback.print_exc()

if __name__ == "__main__":
    main()
