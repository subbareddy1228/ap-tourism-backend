from src.database import engine
from sqlalchemy import text
conn = engine.connect()
r = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'saved_cards'")).fetchall()
for row in r: print(row)
