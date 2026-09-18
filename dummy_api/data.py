"""
In-memory fake database.
Production e eta Postgres / Mongo / real ERP API hobe.
Ekhane structure ta emon vabe rakha hoyeche jate pore shudhu ei layer ta
badle dilei real DB e switch kora jay.
"""

from datetime import datetime, timedelta

# ----------------------------- PRODUCTS -----------------------------
PRODUCTS = [
    {
        "id": "P1001",
        "name": "Aura Wireless Headphone X2",
        "category": "electronics",
        "sub_category": "audio",
        "brand": "Aura",
        "price": 4500,
        "currency": "BDT",
        "rating": 4.6,
        "review_count": 812,
        "stock": 24,
        "tags": ["bluetooth", "noise-cancelling", "over-ear", "40h-battery"],
        "description": "Active noise cancelling over-ear headphone with 40 hour battery.",
    },
    {
        "id": "P1002",
        "name": "Aura Earbuds Lite",
        "category": "electronics",
        "sub_category": "audio",
        "brand": "Aura",
        "price": 1800,
        "currency": "BDT",
        "rating": 4.1,
        "review_count": 1540,
        "stock": 0,
        "tags": ["bluetooth", "in-ear", "budget", "ipx4"],
        "description": "Budget true-wireless earbuds with IPX4 splash resistance.",
    },
    {
        "id": "P1003",
        "name": "NovaBook Air 14 (i5/16GB/512GB)",
        "category": "electronics",
        "sub_category": "laptop",
        "brand": "Nova",
        "price": 92000,
        "currency": "BDT",
        "rating": 4.4,
        "review_count": 233,
        "stock": 7,
        "tags": ["laptop", "ultrabook", "i5", "16gb-ram", "student"],
        "description": "Thin 1.2kg ultrabook, 12 hour battery, good for students.",
    },
    {
        "id": "P1004",
        "name": "NovaBook Pro 16 (i7/32GB/1TB)",
        "category": "electronics",
        "sub_category": "laptop",
        "brand": "Nova",
        "price": 165000,
        "currency": "BDT",
        "rating": 4.7,
        "review_count": 96,
        "stock": 3,
        "tags": ["laptop", "workstation", "i7", "32gb-ram", "video-editing"],
        "description": "Performance laptop for video editing and development work.",
    },
    {
        "id": "P2001",
        "name": "Cotton Panjabi - Off White",
        "category": "fashion",
        "sub_category": "men-ethnic",
        "brand": "Deshi Threads",
        "price": 2200,
        "currency": "BDT",
        "rating": 4.3,
        "review_count": 410,
        "stock": 58,
        "tags": ["panjabi", "cotton", "eid", "men"],
        "description": "Hand stitched cotton panjabi, breathable for summer.",
    },
    {
        "id": "P2002",
        "name": "Jamdani Saree - Red Border",
        "category": "fashion",
        "sub_category": "women-ethnic",
        "brand": "Deshi Threads",
        "price": 7800,
        "currency": "BDT",
        "rating": 4.8,
        "review_count": 121,
        "stock": 12,
        "tags": ["saree", "jamdani", "handloom", "women", "wedding"],
        "description": "Authentic handloom Jamdani saree from Narayanganj weavers.",
    },
    {
        "id": "P2003",
        "name": "Running Shoe Velocity 3",
        "category": "fashion",
        "sub_category": "footwear",
        "brand": "Stride",
        "price": 3900,
        "currency": "BDT",
        "rating": 4.2,
        "review_count": 678,
        "stock": 31,
        "tags": ["shoe", "running", "sports", "unisex"],
        "description": "Lightweight running shoe with cushioned midsole.",
    },
    {
        "id": "P3001",
        "name": "Ceramic Coffee Mug Set (4 pcs)",
        "category": "home",
        "sub_category": "kitchen",
        "brand": "HomeNest",
        "price": 1200,
        "currency": "BDT",
        "rating": 4.0,
        "review_count": 245,
        "stock": 90,
        "tags": ["mug", "ceramic", "gift", "kitchen"],
        "description": "Set of 4 microwave-safe ceramic mugs.",
    },
    {
        "id": "P3002",
        "name": "Air Fryer 5.5L Digital",
        "category": "home",
        "sub_category": "appliance",
        "brand": "HomeNest",
        "price": 8900,
        "currency": "BDT",
        "rating": 4.5,
        "review_count": 502,
        "stock": 15,
        "tags": ["air-fryer", "kitchen", "appliance", "digital"],
        "description": "5.5 litre digital air fryer with 8 preset programs.",
    },
    {
        "id": "P4001",
        "name": "Organic Green Tea (100 bags)",
        "category": "grocery",
        "sub_category": "beverage",
        "brand": "LeafCo",
        "price": 650,
        "currency": "BDT",
        "rating": 4.4,
        "review_count": 1320,
        "stock": 200,
        "tags": ["tea", "organic", "healthy", "beverage"],
        "description": "Organic Sylhet green tea, 100 tea bags.",
    },
]

# ----------------------------- USERS -----------------------------
USERS = {
    "U100": {
        "user_id": "U100",
        "name": "Rafiq Hasan",
        "tier": "gold",
        "city": "Dhaka",
        "preferred_categories": ["electronics", "grocery"],
        "recently_viewed": ["P1001", "P1003", "P3002"],
    },
    "U200": {
        "user_id": "U200",
        "name": "Nusrat Jahan",
        "tier": "silver",
        "city": "Chattogram",
        "preferred_categories": ["fashion", "home"],
        "recently_viewed": ["P2002", "P2001"],
    },
}

# ----------------------------- ORDERS -----------------------------
_now = datetime.utcnow()


def _d(days: int) -> str:
    return (_now - timedelta(days=days)).strftime("%Y-%m-%d")


ORDERS = {
    "ORD-1001": {
        "order_id": "ORD-1001",
        "user_id": "U100",
        "status": "in_transit",
        "placed_on": _d(4),
        "expected_delivery": (_now + timedelta(days=1)).strftime("%Y-%m-%d"),
        "courier": "Pathao Courier",
        "tracking_number": "PTH8891245",
        "payment_method": "bKash",
        "total": 4500,
        "currency": "BDT",
        "shipping_city": "Dhaka",
        "items": [{"product_id": "P1001", "name": "Aura Wireless Headphone X2", "qty": 1, "price": 4500}],
        "timeline": [
            {"date": _d(4), "event": "Order placed"},
            {"date": _d(3), "event": "Payment confirmed"},
            {"date": _d(2), "event": "Packed at Dhaka warehouse"},
            {"date": _d(1), "event": "Handed over to courier"},
        ],
    },
    "ORD-1002": {
        "order_id": "ORD-1002",
        "user_id": "U100",
        "status": "delivered",
        "placed_on": _d(20),
        "delivered_on": _d(15),
        "expected_delivery": _d(15),
        "courier": "Sundarban Courier",
        "tracking_number": "SND5512900",
        "payment_method": "Card",
        "total": 8900,
        "currency": "BDT",
        "shipping_city": "Dhaka",
        "items": [{"product_id": "P3002", "name": "Air Fryer 5.5L Digital", "qty": 1, "price": 8900}],
        "timeline": [
            {"date": _d(20), "event": "Order placed"},
            {"date": _d(18), "event": "Shipped"},
            {"date": _d(15), "event": "Delivered"},
        ],
    },
    "ORD-2001": {
        "order_id": "ORD-2001",
        "user_id": "U200",
        "status": "delivered",
        "placed_on": _d(9),
        "delivered_on": _d(5),
        "expected_delivery": _d(6),
        "courier": "RedX",
        "tracking_number": "RDX7781002",
        "payment_method": "Cash on Delivery",
        "total": 10000,
        "currency": "BDT",
        "shipping_city": "Chattogram",
        "items": [
            {"product_id": "P2002", "name": "Jamdani Saree - Red Border", "qty": 1, "price": 7800},
            {"product_id": "P2001", "name": "Cotton Panjabi - Off White", "qty": 1, "price": 2200},
        ],
        "timeline": [
            {"date": _d(9), "event": "Order placed"},
            {"date": _d(7), "event": "Shipped"},
            {"date": _d(5), "event": "Delivered"},
        ],
    },
    "ORD-2002": {
        "order_id": "ORD-2002",
        "user_id": "U200",
        "status": "cancelled",
        "placed_on": _d(30),
        "expected_delivery": _d(25),
        "courier": None,
        "tracking_number": None,
        "payment_method": "bKash",
        "total": 1200,
        "currency": "BDT",
        "shipping_city": "Chattogram",
        "items": [{"product_id": "P3001", "name": "Ceramic Coffee Mug Set (4 pcs)", "qty": 1, "price": 1200}],
        "timeline": [
            {"date": _d(30), "event": "Order placed"},
            {"date": _d(29), "event": "Cancelled by customer"},
        ],
    },
}

# ----------------------------- RETURNS -----------------------------
RETURNS = {}          # rma_id -> return object
RETURN_COUNTER = {"n": 5000}

RETURN_WINDOW_DAYS = 7
RETURNABLE_STATUS = {"delivered"}
VALID_RETURN_REASONS = [
    "damaged",
    "wrong_item",
    "size_issue",
    "not_as_described",
    "changed_mind",
    "defective",
]

# ----------------------------- POLICY / FAQ -----------------------------
POLICIES = {
    "return": (
        "Delivery hobar 7 din er moddhe return request kora jay. Product unused "
        "and original packaging e thakte hobe. Damaged/defective hole courier "
        "charge company dey, 'changed_mind' hole customer dey."
    ),
    "refund": (
        "Return item warehouse e pouchanor por 3-5 working day er moddhe refund "
        "process hoy. bKash/Card e original payment method e taka fire jay. "
        "Cash on Delivery hole bank/bKash number nite hoy."
    ),
    "shipping": (
        "Dhaka city te 1-2 din, Dhaka er baire 2-4 din. 2000 taka upore order e "
        "delivery charge free. Same day delivery shudhu Dhaka te, dupur 12 tar "
        "age order korle."
    ),
    "warranty": (
        "Electronics e 1 bochor official warranty. Fashion o grocery item e "
        "warranty nei, shudhu return policy apply hoy."
    ),
    "payment": (
        "bKash, Nagad, Rocket, Visa/Mastercard, and Cash on Delivery supported. "
        "50000 taka upore order e COD available na."
    ),
}
