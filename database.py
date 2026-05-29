import sqlite3
from datetime import datetime

DB_NAME = "gift_garantor.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            rub_balance REAL DEFAULT 0,
            usdt_balance REAL DEFAULT 0,
            ton_balance REAL DEFAULT 0,
            star_balance REAL DEFAULT 0,
            deals_success INTEGER DEFAULT 0,
            rub_details TEXT,
            usdt_details TEXT,
            ton_details TEXT,
            star_details TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deals (
            deal_id INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_number INTEGER UNIQUE,
            seller_id INTEGER,
            buyer_id INTEGER,
            amount REAL,
            currency TEXT,
            description TEXT,
            status TEXT,
            role TEXT,
            created_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
        return get_user(user_id)
    
    return {
        "user_id": user[0],
        "username": user[1],
        "rub_balance": user[2],
        "usdt_balance": user[3],
        "ton_balance": user[4],
        "star_balance": user[5],
        "deals_success": user[6],
        "rub_details": user[7],
        "usdt_details": user[8],
        "ton_details": user[9],
        "star_details": user[10],
    }

def update_user_balance(user_id, currency, amount):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {currency.lower()}_balance = {currency.lower()}_balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def update_user_deals_success(user_id, amount):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET deals_success = deals_success + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def update_user_details(user_id, currency, details):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {currency.lower()}_details = ? WHERE user_id = ?", (details, user_id))
    conn.commit()
    conn.close()

def delete_user_details(user_id, currency):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {currency.lower()}_details = NULL WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_next_deal_number():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(deal_number) FROM deals")
    max_num = cursor.fetchone()[0]
    conn.close()
    return (max_num + 1) if max_num else 1

def create_deal(seller_id, amount, currency, description, role, deal_number):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO deals (deal_number, seller_id, amount, currency, description, status, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (deal_number, seller_id, amount, currency, description, "waiting_buyer", role, datetime.now().isoformat()))
    deal_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return deal_id

def get_deal_by_number(deal_number):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM deals WHERE deal_number = ?", (deal_number,))
    deal = cursor.fetchone()
    conn.close()
    if deal:
        return {
            "deal_id": deal[0],
            "deal_number": deal[1],
            "seller_id": deal[2],
            "buyer_id": deal[3],
            "amount": deal[4],
            "currency": deal[5],
            "description": deal[6],
            "status": deal[7],
            "role": deal[8],
            "created_at": deal[9],
        }
    return None

def join_deal(deal_number, buyer_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE deals SET buyer_id = ?, status = ? WHERE deal_number = ?", (buyer_id, "waiting_payment", deal_number))
    conn.commit()
    conn.close()

def update_deal_status(deal_number, status):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE deals SET status = ? WHERE deal_number = ?", (status, deal_number))
    conn.commit()
    conn.close()

def get_user_deals(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM deals WHERE seller_id = ? OR buyer_id = ? ORDER BY created_at DESC", (user_id, user_id))
    deals = cursor.fetchall()
    conn.close()
    return deals

def complete_deal(deal_number):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT seller_id, buyer_id, amount, currency FROM deals WHERE deal_number = ?", (deal_number,))
    deal = cursor.fetchone()
    if deal:
        update_user_balance(deal[0], deal[3], deal[2])
        update_user_deals_success(deal[0], 1)
        update_user_deals_success(deal[1], 1)
        cursor.execute("UPDATE deals SET status = ? WHERE deal_number = ?", ("completed", deal_number))
        conn.commit()
        conn.close()
        return deal
    conn.close()
    return None

def get_user_rekv(user_id, currency):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"SELECT {currency.lower()}_details FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None