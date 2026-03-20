import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import Base, engine

# import all models so SQLAlchemy knows about them
from src.models.temple import Temple, TempleEvent, TempleReview
from src.models.darshan import (
    DarshanType, DarshanSlot, DarshanBooking,
    PoojaService, PoojaSlot, PoojaBooking,
    PrasadamItem, PrasadamOrder, PrasadamOrderItem,
)

def init():
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Done! All tables created.")

if __name__ == "__main__":
    init()