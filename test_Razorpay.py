import hmac
import hashlib
import requests

KEY_ID     = "rzp_test_SaWfnSU89Lq5eA"
KEY_SECRET = "fr2vbaGz7uwV83kLafIWjGk5"
BASE_URL   = "http://localhost:8000/api/v1"
TOKEN      = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjMzc0ZmQ5NC1kNWI4LTQ0YWItYjdlOS1lM2E5NTFmNDNiZjgiLCJyb2xlIjoidHJhdmVsZXIiLCJ0eXBlIjoiYWNjZXNzIiwianRpIjoiMjg3ZTVhMmUtZDI0NS00NjQ5LTgyNGMtMzRmOTExZGQwMmRjIiwiZXhwIjoxNzc1Njk3NDI3LCJpYXQiOjE3NzU2MTEwMjd9.YFHMx6rFg2MNr7eZBEa2ydDbTYjNTd4k8SctVsMs5Gk"

# ── Step 1: Create fresh order via YOUR api ──────
order_resp = requests.post(
    f"{BASE_URL}/wallet/topup",
    json={"amount": 1000},
    headers={"Authorization": f"Bearer {TOKEN}"}
)
print("Order:", order_resp.json())
ORDER_ID = order_resp.json()["data"]["order_id"]
print("✅ Order ID:", ORDER_ID)

# ── Step 2: Manually authorize via Razorpay ──────
# Use Razorpay's test payment endpoint correctly
pay = requests.post(
    f"https://api.razorpay.com/v1/orders/{ORDER_ID}/payments",
    auth=(KEY_ID, KEY_SECRET),
)
print("Payments on order:", pay.status_code, pay.json())

# Extract payment_id from order's linked payments
payments = pay.json().get("items", [])
if payments:
    payment_id = payments[0]["id"]
else:
    print("❌ No payments found — manually set payment_id below")
    payment_id = input("Paste payment_id from Razorpay dashboard: ")

print("✅ Payment ID:", payment_id)

# ── Step 3: Generate signature ───────────────────
signature = hmac.new(
    KEY_SECRET.encode(),
    f"{ORDER_ID}|{payment_id}".encode(),
    hashlib.sha256
).hexdigest()
print("✅ Signature:", signature)

# ── Step 4: Verify ────────────────────────────────
verify = requests.post(
    f"{BASE_URL}/wallet/topup/verify",
    json={
        "razorpay_order_id":   ORDER_ID,
        "razorpay_payment_id": payment_id,
        "razorpay_signature":  signature,
    },
    headers={"Authorization": f"Bearer {TOKEN}"}
)
print("✅ Verify:", verify.json())


