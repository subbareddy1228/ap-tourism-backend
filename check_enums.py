from src.database import engine
from sqlalchemy import text
conn = engine.connect()
r = conn.execute(text("SELECT unnest(enum_range(NULL::paymentstatus))")).fetchall()
print('status:', r)
r2 = conn.execute(text("SELECT unnest(enum_range(NULL::paymentmethod))")).fetchall()
print('method:', r2)
