import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add root directory to path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, root_dir)
print("sys.path:", sys.path)
print("root_dir content:", os.listdir(root_dir))

from app.core.config import settings

print("SUPABASE_URL:", settings.SUPABASE_URL)
print("SUPABASE_KEY exists:", bool(settings.SUPABASE_KEY))
print("SUPABASE_SERVICE_ROLE_KEY exists:", bool(settings.SUPABASE_SERVICE_ROLE_KEY))

from sqlmodel import Session, select
from app.db.session import engine, init_db
from app.models.user import User
from app.models.token import TokenWallet

try:
    init_db()
    print("Database init succeeded.")
except Exception as e:
    print("Database init failed:", e)

with Session(engine) as session:
    try:
        users = session.exec(select(User)).all()
        print(f"Query user table succeeded: found {len(users)} users.")
        for u in users:
            print(f"User: {u.id}, {u.email}, plan: {u.plan}")
    except Exception as e:
        print("Query user table failed:", e)

    try:
        wallets = session.exec(select(TokenWallet)).all()
        print(f"Query token_wallet table succeeded: found {len(wallets)} wallets.")
    except Exception as e:
        print("Query token_wallet table failed:", e)
