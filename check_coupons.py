from src.database import engine
from sqlalchemy import text
conn = engine.connect()
r = conn.execute(text('SELECT code, is_public FROM coupons LIMIT 10')).fetchall()
print(r)
