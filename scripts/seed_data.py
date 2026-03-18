"""
seed_data.py — Insert test data for Tirumala temple
Run: python scripts/seed_data.py
This inserts data in correct order:
1. Temple
2. Temple Event
3. Darshan Types
4. Darshan Slots (next 7 days)
5. Pooja Services
6. Pooja Slots
7. Prasadam Items
"""

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, time, timedelta
from uuid import uuid4

from src.core.database import AsyncSessionLocal
from src.models.temple import Temple, TempleEvent
from src.models.darshan import (
    DarshanType, DarshanType, DarshanSlot,
    PoojaService, PoojaSlot,
    PrasadamItem,
)


async def seed():
    async with AsyncSessionLocal() as db:
        print("Starting seed...")

        # ─────────────────────────────────────────────
        # 1. Temple
        # ─────────────────────────────────────────────
        temple = Temple(
            id=uuid4(),
            name="Tirumala Venkateswara Temple",
            description="One of the most visited religious sites in the world, dedicated to Lord Venkateswara.",
            deity="Vishnu",
            district="Tirupati",
            address="Tirumala, Tirupati, Andhra Pradesh 517504",
            latitude=13.6834,
            longitude=79.3474,
            dress_code="Men must wear dhoti or pyjama. Women must wear saree or salwar kameez.",
            contact_number="08772277777",
            website="https://tirumala.org",
            timings={
                "monday":    {"open": "02:30", "close": "01:00"},
                "tuesday":   {"open": "02:30", "close": "01:00"},
                "wednesday": {"open": "02:30", "close": "01:00"},
                "thursday":  {"open": "02:30", "close": "01:00"},
                "friday":    {"open": "02:30", "close": "01:00"},
                "saturday":  {"open": "02:30", "close": "01:00"},
                "sunday":    {"open": "02:30", "close": "01:00"},
            },
            images=[],
            is_featured=True,
            is_active=True,
            booking_count=0,
        )
        db.add(temple)
        await db.flush()
        print(f"Temple created: {temple.id}")

        # ─────────────────────────────────────────────
        # 2. Temple Event
        # ─────────────────────────────────────────────
        event = TempleEvent(
            id=uuid4(),
            temple_id=temple.id,
            name="Brahmotsavam Festival",
            description="Annual festival celebrated for 9 days with grand processions.",
            event_date=date.today() + timedelta(days=30),
            start_time=time(6, 0),
            end_time=time(22, 0),
            is_active=True,
        )
        db.add(event)

        # ─────────────────────────────────────────────
        # 3. Darshan Types
        # ─────────────────────────────────────────────
        free_darshan = DarshanType(
            id=uuid4(),
            temple_id=temple.id,
            name="Free Darshan",
            darshan_type="FREE",
            description="Standard free darshan for all devotees. Wait time may be 6-20 hours.",
            price=0.0,
            duration_minutes=30,
            what_is_included="Entry to main sanctum, Tirtha prasadam",
            max_persons_per_booking=6,
            is_active=True,
        )

        special_darshan = DarshanType(
            id=uuid4(),
            temple_id=temple.id,
            name="Special Entry Darshan",
            darshan_type="SPECIAL_ENTRY",
            description="Special entry darshan with shorter wait time.",
            price=300.0,
            duration_minutes=20,
            what_is_included="Special entry, Laddu prasadam, Tirtha",
            max_persons_per_booking=4,
            is_active=True,
        )

        suprabhata = DarshanType(
            id=uuid4(),
            temple_id=temple.id,
            name="Suprabhata Seva",
            darshan_type="SUPRABHATA",
            description="Early morning seva at 3:00 AM with exclusive access.",
            price=500.0,
            duration_minutes=45,
            what_is_included="Suprabhata seva, Prasadam, Special blessing",
            max_persons_per_booking=2,
            is_active=True,
        )

        vip_darshan = DarshanType(
            id=uuid4(),
            temple_id=temple.id,
            name="VIP Darshan",
            darshan_type="VIP",
            description="VIP darshan with immediate entry and personal attention.",
            price=1500.0,
            duration_minutes=60,
            what_is_included="VIP entry, Close darshan, Laddu, Silk vastra, Tirtha",
            max_persons_per_booking=2,
            is_active=True,
        )

        db.add_all([free_darshan, special_darshan, suprabhata, vip_darshan])
        await db.flush()
        print("Darshan types created: FREE, SPECIAL_ENTRY, SUPRABHATA, VIP")

        # ─────────────────────────────────────────────
        # 4. Darshan Slots — next 7 days
        # ─────────────────────────────────────────────
        slot_configs = [
            (free_darshan.id,    time(6, 0),  time(10, 0), 1000),
            (free_darshan.id,    time(10, 0), time(14, 0), 1000),
            (free_darshan.id,    time(14, 0), time(18, 0), 1000),
            (special_darshan.id, time(7, 0),  time(9, 0),  300),
            (special_darshan.id, time(15, 0), time(17, 0), 300),
            (suprabhata.id,      time(3, 0),  time(4, 0),  50),
            (vip_darshan.id,     time(8, 0),  time(9, 0),  20),
            (vip_darshan.id,     time(16, 0), time(17, 0), 20),
        ]

        today = date.today()
        for i in range(7):
            slot_date = today + timedelta(days=i)
            for darshan_type_id, start, end, quota in slot_configs:
                slot = DarshanSlot(
                    id=uuid4(),
                    temple_id=temple.id,
                    darshan_type_id=darshan_type_id,
                    slot_date=slot_date,
                    start_time=start,
                    end_time=end,
                    total_quota=quota,
                    booked_count=0,
                    is_active=True,
                )
                db.add(slot)

        print("Darshan slots created for next 7 days")

        # ─────────────────────────────────────────────
        # 5. Pooja Services
        # ─────────────────────────────────────────────
        archana = PoojaService(
            id=uuid4(),
            temple_id=temple.id,
            name="Archana",
            description="Basic archana with flowers and mantras dedicated to Lord Venkateswara.",
            price=116.0,
            duration_minutes=15,
            items_included="Flowers, kumkum, vibhuti, prasadam",
            priest_requirements="One priest required",
            max_persons=10,
            is_active=True,
        )

        kalyanam = PoojaService(
            id=uuid4(),
            temple_id=temple.id,
            name="Kalyanotsavam",
            description="Celestial wedding ceremony of Lord Venkateswara and Goddess Padmavathi.",
            price=500.0,
            duration_minutes=60,
            items_included="Silk vastras, flowers, special prasadam, Laddu",
            priest_requirements="Two priests required with Vedic chanting",
            max_persons=6,
            is_active=True,
        )

        abhishekam = PoojaService(
            id=uuid4(),
            temple_id=temple.id,
            name="Abhishekam",
            description="Sacred bathing ritual of the deity with milk, honey and holy water.",
            price=750.0,
            duration_minutes=45,
            items_included="Milk, honey, rose water, special prasadam",
            priest_requirements="Three priests required",
            max_persons=4,
            is_active=True,
        )

        db.add_all([archana, kalyanam, abhishekam])
        await db.flush()
        print("Pooja services created: Archana, Kalyanotsavam, Abhishekam")

        # ─────────────────────────────────────────────
        # 6. Pooja Slots — next 7 days
        # ─────────────────────────────────────────────
        pooja_configs = [
            (archana.id,   time(7, 0),  time(8, 0),  50),
            (archana.id,   time(11, 0), time(12, 0), 50),
            (archana.id,   time(16, 0), time(17, 0), 50),
            (kalyanam.id,  time(9, 0),  time(10, 0), 20),
            (kalyanam.id,  time(15, 0), time(16, 0), 20),
            (abhishekam.id, time(6, 0), time(7, 0),  10),
            (abhishekam.id, time(18, 0), time(19, 0), 10),
        ]

        for i in range(7):
            slot_date = today + timedelta(days=i)
            for service_id, start, end, quota in pooja_configs:
                slot = PoojaSlot(
                    id=uuid4(),
                    temple_id=temple.id,
                    pooja_service_id=service_id,
                    slot_date=slot_date,
                    start_time=start,
                    end_time=end,
                    total_quota=quota,
                    booked_count=0,
                    is_active=True,
                )
                db.add(slot)

        print("Pooja slots created for next 7 days")

        # ─────────────────────────────────────────────
        # 7. Prasadam Items
        # ─────────────────────────────────────────────
        laddu = PrasadamItem(
            id=uuid4(),
            temple_id=temple.id,
            name="Tirupati Laddu",
            description="Famous Tirupati laddu made with besan, sugar and dry fruits.",
            price=50.0,
            weight_grams=175,
            image_url=None,
            is_available=True,
        )

        vada = PrasadamItem(
            id=uuid4(),
            temple_id=temple.id,
            name="Vada Prasadam",
            description="Sacred vada offered as prasadam to Lord Venkateswara.",
            price=25.0,
            weight_grams=100,
            image_url=None,
            is_available=True,
        )

        pongal = PrasadamItem(
            id=uuid4(),
            temple_id=temple.id,
            name="Pongal Prasadam",
            description="Sweet pongal prasadam prepared in TTD kitchens.",
            price=30.0,
            weight_grams=200,
            image_url=None,
            is_available=True,
        )

        db.add_all([laddu, vada, pongal])

        await db.commit()
        print("\nSeed completed successfully!")
        print(f"\nTemple ID (use this in all endpoints): {temple.id}")


if __name__ == "__main__":
    asyncio.run(seed())