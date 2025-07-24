from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import os
import csv
from datetime import datetime

app = Flask(__name__)
CORS(app)
init_db()

DB_FILE = "gustanto_pos.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item TEXT,
                price INTEGER,
                timestamp TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount INTEGER,
                description TEXT,
                timestamp TEXT
            )
        ''')
        conn.commit()

init_db()

@app.route('/')
def home():
    return "✅ Gustanto POS Backend is live!"
@app.route('/order', methods=['POST'])
def save_order():
    data = request.json
    timestamp = data.get('timestamp', datetime.now().isoformat())
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        for item in data['order']:
            c.execute("INSERT INTO sales (item, price, timestamp) VALUES (?, ?, ?)", (item['name'], item['price'], timestamp))
        conn.commit()
    return jsonify({"status": "success"})

@app.route('/expense', methods=['POST'])
def add_expense():
    data = request.json
    timestamp = data.get('timestamp', datetime.now().isoformat())
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO expenses (amount, description, timestamp) VALUES (?, ?, ?)", (data['amount'], data['description'], timestamp))
        conn.commit()
    return jsonify({"status": "expense saved"})

@app.route('/sales/today')
def today_sales():
    date = datetime.now().date().isoformat()
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT item, price FROM sales WHERE DATE(timestamp)=?", (date,))
        sales = c.fetchall()
        total = sum(row[1] for row in sales)
        c.execute("SELECT amount FROM expenses WHERE DATE(timestamp)=?", (date,))
        expenses = sum(row[0] for row in c.fetchall())
    return jsonify({"sales": sales, "total_sales": total, "expenses": expenses, "net_profit": total - expenses})

@app.route('/sales/month')
def month_sales():
    month = request.args.get('filter', default=datetime.now().strftime('%Y-%m'))
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT item, price, timestamp FROM sales WHERE strftime('%Y-%m', timestamp)=?", (month,))
        sales = c.fetchall()
        c.execute("SELECT amount FROM expenses WHERE strftime('%Y-%m', timestamp)=?", (month,))
        expenses = sum(row[0] for row in c.fetchall())
        total = sum(row[1] for row in sales)
    return jsonify({"sales": sales, "total_sales": total, "expenses": expenses, "net_profit": total - expenses})

@app.route('/export/<period>')
def export_csv(period):
    filename = f"sales_{period}.csv"
    with sqlite3.connect(DB_FILE) as conn, open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Item', 'Price', 'Timestamp'])
        c = conn.cursor()
        if period == 'today':
            date = datetime.now().date().isoformat()
            c.execute("SELECT item, price, timestamp FROM sales WHERE DATE(timestamp)=?", (date,))
        elif period == 'month':
            month = datetime.now().strftime('%Y-%m')
            c.execute("SELECT item, price, timestamp FROM sales WHERE strftime('%Y-%m', timestamp)=?", (month,))
        else:
            return jsonify({"error": "Invalid period"})
        for row in c.fetchall():
            writer.writerow(row)
    return send_file(filename, as_attachment=True)

@app.route('/chart/month')
def chart_month():
    month = request.args.get('filter', default=datetime.now().strftime('%Y-%m'))
    daily_data = {}
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT price, timestamp FROM sales WHERE strftime('%Y-%m', timestamp)=?", (month,))
        for price, ts in c.fetchall():
            date = ts[:10]
            daily_data.setdefault(date, {'sales': 0, 'expenses': 0})
            daily_data[date]['sales'] += price
        c.execute("SELECT amount, timestamp FROM expenses WHERE strftime('%Y-%m', timestamp)=?", (month,))
        for amount, ts in c.fetchall():
            date = ts[:10]
            daily_data.setdefault(date, {'sales': 0, 'expenses': 0})
            daily_data[date]['expenses'] += amount
    result = []
    for date in sorted(daily_data):
        entry = daily_data[date]
        result.append({
            'date': date,
            'sales': entry['sales'],
            'expenses': entry['expenses'],
            'net_profit': entry['sales'] - entry['expenses']
        })
    return jsonify(result)
@app.route('/sales', methods=['GET', 'POST'])
def sales():
    if request.method == 'GET':
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM sales ORDER BY timestamp DESC")
            sales = [
                {"id": row[0], "item": row[1], "price": row[2], "timestamp": row[3]}
                for row in c.fetchall()
            ]
        return jsonify(sales)

    if request.method == 'POST':
        data = request.get_json()
        item = data['item']
        price = data['price']
        timestamp = data['timestamp']

        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO sales (item, price, timestamp) VALUES (?, ?, ?)", (item, price, timestamp))
            conn.commit()

        return jsonify({"message": "Sale saved successfully!"}), 201



    data = request.get_json()
    item = data['item']
    price = data['price']
    timestamp = data['timestamp']

    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO sales (item, price, timestamp) VALUES (?, ?, ?)", (item, price, timestamp))
        conn.commit()

    return jsonify({"message": "Sale saved successfully!"}), 201



    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM sales ORDER BY timestamp DESC")
        sales = [
            {"id": row[0], "item": row[1], "price": row[2], "timestamp": row[3]}
            for row in c.fetchall()
        ]
    return jsonify(sales)

if __name__ == '__main__':
    app.run(debug=True)
