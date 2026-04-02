from flask import Flask, request, jsonify, send_from_directory, g
from flask_cors import CORS
import mysql.connector
from datetime import datetime
from config import DB_CONFIG
import sys

app = Flask(__name__, static_folder='../frontend')
CORS(app, resources={
    r"/availability": {"origins": "*"},
    r"/booking": {"origins": "*"}
})

# Database connection helper with error handling
def get_db():
    if 'db' not in g:
        try:
            g.db = mysql.connector.connect(**DB_CONFIG)
            print("Successfully connected to database", file=sys.stderr)
        except mysql.connector.Error as err:
            print(f"Database connection error: {err}", file=sys.stderr)
            return None
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Serve frontend
@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

# API Endpoints with error handling
@app.route('/availability')
def check_availability():
    try:
        city = request.args.get('city')
        start_date = request.args.get('start')
        end_date = request.args.get('end')  

        if not all([city, start_date, end_date]):
            return jsonify({"error": "Missing parameters"}), 400

        db = get_db()
        if db is None:
            return jsonify({"error": "Database connection failed"}), 500
            
        cursor = db.cursor(dictionary=True)

        # Availability check based only on the start_date
        query = """
        SELECT DISTINCT
               v.vehicle_id as id, 
               v.make, 
               v.model, 
               v.model_year as year, 
               r.daily_rate, 
               v.img_uri as image_url, 
               p.name as partner,
               vc.label as type
        FROM vehicle v
        JOIN partner p ON v.partner_id = p.partner_id 
        JOIN city c ON p.city_id = c.city_id 
        JOIN rate_plan r ON v.vehicle_id = r.vehicle_id 
        JOIN vehicle_class vc ON v.class_id = vc.class_id
        WHERE c.name = %s
          AND r.start_date <= %s 
          AND r.end_date >= %s 
          AND v.active_flag = 1
          AND v.vehicle_id IN (
              SELECT DISTINCT vehicle_id
              FROM inventory_cal
              WHERE start_date = %s
                AND available_units > 0
          )
        """
        cursor.execute(query, (
            city, start_date, start_date,  # rate plan must be valid for that day
            start_date                      # availability check only on start date
        ))

        results = cursor.fetchall()

        if not results:
            return jsonify({"message": "No vehicles found for the specified criteria."}), 200
        
        return jsonify({"available_vehicles": results}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()

@app.route('/booking', methods=['POST'])
def create_booking():
    try:
        data = request.get_json()
        print("Received booking data:", data)
        
        # Convert total_amount from "1,000 MAD" to 1000.00
        total_amount = float(data['total_amount'].replace(' MAD', '').replace(',', ''))
        
        db = get_db()
        cursor = db.cursor(dictionary=True)
        
        # Check if customer is blacklisted by ID number
        cursor.execute("""
            SELECT * FROM blacklist 
            WHERE customer_id IN (
                SELECT customer_id FROM customer 
                WHERE id_number = %s
            ) 
            AND active_flag = 1
        """, (data['id_number'],))
        
        blacklisted = cursor.fetchone()
        if blacklisted:
            return jsonify({
                "error": "BOOKING_REJECTED",
                "message": "This customer is blacklisted and cannot make bookings",
                "reason": blacklisted.get('reason', 'Not specified')
            }), 403
        
        # Create customer
        cursor.execute("""
            INSERT INTO customer (
                first_name, last_name, email, nationality, phone,
                id_type, id_number
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                data['first_name'],
                data['last_name'],
                data['email'],
                data['nationality'],
                data['phone'],
                data['id_type'],
                data['id_number']
            ))
        customer_id = cursor.lastrowid
        
        # Create booking (using vehicle_id=1 temporarily)
        cursor.execute("""
            INSERT INTO booking (
                customer_id, vehicle_id, start_date, end_date,
                total_price, currency, source_channel
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                customer_id,
                1,  # TEMPORARY: Hardcoded vehicle_id
                data['start_date'],
                data['end_date'],
                total_amount,
                'MAD',
                'DIRECT'
            ))
        booking_id = cursor.lastrowid
        
        # Create payment record
        cursor.execute("""
            INSERT INTO payment (
                booking_id, gateway, amount, currency
            ) VALUES (%s, %s, %s, %s)
            """, (
                booking_id,
                data['payment_method'],
                total_amount,
                'MAD'
            ))
        
        db.commit()
        return jsonify({
            "booking_id": booking_id,
            "status": "CONFIRMED"
        }), 201

    except Exception as e:
        db.rollback()
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 400
    finally:
        if 'cursor' in locals(): cursor.close()
if __name__ == '__main__':
    app.run(debug=True, port=5000)