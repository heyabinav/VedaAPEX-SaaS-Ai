from sqlmodel import Session, select
from app.db.session import engine, init_db
from app.models.token import AIGenerationHistory

# Ensure all models are imported/registered
init_db()

with Session(engine) as s:
    rows = s.exec(select(AIGenerationHistory).order_by(AIGenerationHistory.created_at.desc()).limit(20)).all()
    for r in rows:
        print(r.id, r.user_id, r.type, r.status, r.provider, r.cost, r.output_url, (r.prompt[:120] + '...') if r.prompt and len(r.prompt) > 120 else r.prompt, r.created_at)
