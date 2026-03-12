from src.database import engine
from sqlalchemy import text
conn = engine.connect()
r = conn.execute(text('SELECT unnest(enum_range(NULL::couponapplicableto))')).fetchall()
print(r)
