import os
from dotenv import load_dotenv

load_dotenv()
os.environ["AFP_USE_MOCK_DB"] = "false"

from app.db.supabase_client import supabase

def main():
    print("Testing select of semantic_score...")
    try:
        res = supabase.table("afp_bom_product_suggestions").select("semantic_score").limit(1).execute()
        print("Success! Column exists. Data:", res.data)
    except Exception as e:
        print("Failed:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
