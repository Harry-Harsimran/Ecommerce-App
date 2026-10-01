

import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "ecommerce.db"

CATEGORIES = {
    "Electronics": (50, 800),
    "Clothing": (10, 150),
    "Home & Kitchen": (15, 300),
    "Books": (5, 60),
    "Beauty": (8, 120),
    "Sports": (20, 250),
    "Toys": (10, 100),
    "Furniture": (100, 900),
}

PRODUCT_NAMES = {
    "Electronics": ["Wireless Earbuds", "Bluetooth Speaker", "Smartwatch", "Laptop Stand", "Power Bank"],
    "Clothing": ["Cotton T-Shirt", "Denim Jacket", "Running Shoes", "Wool Sweater", "Summer Dress"],
    "Home & Kitchen": ["Air Fryer", "Blender", "Cookware Set", "Vacuum Cleaner", "Coffee Maker"],
    "Books": ["Fiction Novel", "Cookbook", "Self-Help Guide", "Biography", "Comic Book"],
    "Beauty": ["Face Serum", "Lipstick Set", "Hair Dryer", "Perfume", "Skincare Kit"],
    "Sports": ["Yoga Mat", "Dumbbell Set", "Cycling Helmet", "Tennis Racket", "Football"],
    "Toys": ["Building Blocks", "RC Car", "Puzzle Set", "Action Figure", "Board Game"],
    "Furniture": ["Office Chair", "Bookshelf", "Study Desk", "Bed Frame", "Sofa Cushion"],
}

CITIES = [
    ("Mumbai", "MH"), ("Delhi", "DL"), ("Bengaluru", "KA"), ("Chennai", "TN"),
    ("Kolkata", "WB"), ("Hyderabad", "TG"), ("Pune", "MH"), ("Ahmedabad", "GJ"),
    ("Jaipur", "RJ"), ("Ludhiana", "PB"), ("Lucknow", "UP"), ("Chandigarh", "CH"),
]

PAYMENT_TYPES = ["Credit Card", "Debit Card", "UPI", "Net Banking", "Cash on Delivery"]

FIRST_NAMES = ["Aarav", "Vivaan", "Ishaan", "Ananya", "Priya", "Riya", "Karan", "Simran",
               "Rohan", "Neha", "Aditya", "Meera", "Arjun", "Sanya", "Kabir", "Diya",
               "Harsh", "Pooja", "Nikhil", "Tanya"]
LAST_NAMES = ["Sharma", "Verma", "Singh", "Kapoor", "Gupta", "Mehta", "Reddy", "Iyer",
              "Nair", "Chopra", "Malhotra", "Joshi", "Bhatia", "Rao", "Kaur"]


def random_date(start, end):
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days),
                              seconds=random.randint(0, 86399))


def build_schema(conn):
    conn.execute("DROP TABLE IF EXISTS sales")
    conn.execute("""
        CREATE TABLE sales (
            order_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            order_date      TEXT NOT NULL,
            customer_name   TEXT NOT NULL,
            customer_city   TEXT NOT NULL,
            customer_state  TEXT NOT NULL,
            product_name    TEXT NOT NULL,
            category        TEXT NOT NULL,
            quantity        INTEGER NOT NULL,
            unit_price      REAL NOT NULL,
            unit_cost       REAL NOT NULL,
            revenue         REAL NOT NULL,
            profit          REAL NOT NULL,
            payment_type    TEXT NOT NULL,
            order_status    TEXT NOT NULL
        )
    """)
    conn.commit()


def generate_rows(n=200):
    start = datetime(2024, 1, 1)
    end = datetime(2024, 12, 31)
    rows = []
    # simulate a repeat-customer pool so LTV/repeat-rate queries have signal
    customer_pool = [f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}" for _ in range(70)]

    for _ in range(n):
        category = random.choice(list(CATEGORIES.keys()))
        low, high = CATEGORIES[category]
        unit_price = round(random.uniform(low, high), 2)
        unit_cost = round(unit_price * random.uniform(0.55, 0.75), 2)
        quantity = random.randint(1, 4)
        revenue = round(unit_price * quantity, 2)
        profit = round((unit_price - unit_cost) * quantity, 2)
        city, state = random.choice(CITIES)
        order_status = random.choices(
            ["delivered", "shipped", "cancelled", "returned"],
            weights=[80, 10, 5, 5]
        )[0]

        rows.append((
            random_date(start, end).strftime("%Y-%m-%d %H:%M:%S"),
            random.choice(customer_pool),
            city,
            state,
            random.choice(PRODUCT_NAMES[category]),
            category,
            quantity,
            unit_price,
            unit_cost,
            revenue,
            profit,
            random.choice(PAYMENT_TYPES),
            order_status,
        ))
    return rows


def main():
    conn = sqlite3.connect(DB_PATH)
    build_schema(conn)
    rows = generate_rows(200)
    conn.executemany("""
        INSERT INTO sales (
            order_date, customer_name, customer_city, customer_state,
            product_name, category, quantity, unit_price, unit_cost,
            revenue, profit, payment_type, order_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
    print(f"Inserted {count} rows into {DB_PATH}")
    conn.close()


if __name__ == "__main__":
    main()
