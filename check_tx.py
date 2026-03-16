from src.database import engine
from sqlalchemy import text
conn = engine.connect()
r = conn.execute(text("""
    SELECT column_name, data_type, is_nullable 
    FROM information_schema.columns 
    WHERE table_name = 'transactions'
""")).fetchall()
for row in r: print(row)
