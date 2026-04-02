import mysql.connector
from config import DB_CONFIG
from datetime import datetime, timedelta

def insert_sample_data():
    try:
        # Connect to database
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("Connected to database, inserting sample data...")

        # Clear existing data
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        tables = [
            'inventory_cal', 'rate_plan', 'booking', 'payment', 'csr_donation',
            'review', 'maintenance', 'vehicle', 'vehicle_class', 
            'partner', 'city'
        ]
        for table in tables:
            cursor.execute(f"TRUNCATE TABLE {table}")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        
        # Insert sample city
        cursor.execute("""
            INSERT INTO city (name, region) 
            VALUES ('Essaouira', 'Marrakech-Safi')
        """)
        city_id = cursor.lastrowid
        
        # Insert sample partner
        cursor.execute("""
            INSERT INTO partner (name, city_id, contact_email, contact_phone, rental_agency_flag) 
            VALUES ('EcoViaDrive Office', %s, 'hello@ecoviadrive.ma', '+212639927999', 1)
        """, (city_id,))
        partner_id = cursor.lastrowid
        
        # Insert vehicle classes 
        vehicle_classes = [
            ('HATCHBACK', 5, 'MANUAL', 'GASOLINE'),
            ('SEDAN', 5, 'MANUAL', 'GASOLINE'),
            ('SEDAN', 5, 'AUTO', 'GASOLINE'),
            ('HATCHBACK', 5, 'MANUAL', 'DIESEL')
        ]
        
        class_ids = []
        for vc in vehicle_classes:
            cursor.execute("""
                INSERT INTO vehicle_class (label, seats, transmission, fuel_type)
                VALUES (%s, %s, %s, %s)
            """, vc)
            class_ids.append(cursor.lastrowid)
        
        # Insert vehicles with colors 
        try:
            cursor.execute("ALTER TABLE vehicle ADD COLUMN color VARCHAR(50)")
        except mysql.connector.Error as err:
            # Column likely already exists
            pass
        
        # Insert 7 vehicles with model_year as integer (2022) and color 
        vehicles = [
            # 2 Black Sanderos (HATCHBACK, Manual, Gasoline)
            (partner_id, class_ids[0], 'ABC123', 'Dacia', 'Sandero', 2022, 'black', '/images/sanderoblack.jpg'),
            (partner_id, class_ids[0], 'ABC124', 'Dacia', 'Sandero', 2022, 'black', '/images/sanderoblack.jpg'),
            
            # 2 Dark Grey Sanderos (1 Gasoline, 1 Diesel)
            (partner_id, class_ids[0], 'DEF123', 'Dacia', 'Sandero', 2022, 'dark grey', '/images/sanderodarkgrey.jpg'),
            (partner_id, class_ids[3], 'DEF124', 'Dacia', 'Sandero', 2022, 'dark grey', '/images/sanderodarkgrey.jpg'),
            
            # 3 White Logans (2 Manual, 1 Automatic)
            (partner_id, class_ids[1], 'GHI123', 'Dacia', 'Logan', 2022, 'white', '/images/loganwhite.jpg'),
            (partner_id, class_ids[2], 'GHI124', 'Dacia', 'Logan', 2022, 'white', '/images/loganwhite.jpg'),
            (partner_id, class_ids[1], 'GHI125', 'Dacia', 'Logan', 2022, 'white', '/images/loganwhite.jpg')
        ]
        
        vehicle_ids = []
        for v in vehicles:
            cursor.execute("""
                INSERT INTO vehicle (partner_id, class_id, reg_plate, make, model, model_year, color, img_uri)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, v)
            vehicle_ids.append(cursor.lastrowid)

        # Insert a blacklisted customer
        cursor.execute("""
            INSERT INTO customer (
                first_name, last_name, email, nationality, phone,
                id_type, id_number
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            "abir", "boukchouch", "abir@example.com", 
            "Morocco", "+212600000000", "CIN", "EE123456"
        ))

        blacklisted_customer_id = cursor.lastrowid

        # Add to blacklist
        cursor.execute("""
            INSERT INTO blacklist (
                customer_id, reason
            ) VALUES (%s, %s)
        """, (
            blacklisted_customer_id, 
            "Previous damage to vehicle and non-payment"
        ))
                
        # Insert rate plans for all vehicles
        today = datetime.now().date()
        for v_id in vehicle_ids:
            cursor.execute("""
                INSERT INTO rate_plan (vehicle_id, daily_rate, start_date, end_date)
                VALUES (%s, %s, %s, %s)
            """, (v_id, 250.00, today, today + timedelta(days=365)))

        # Set up availability calendar
        # Today: 5 vehicles available (vehicle_ids 0,1,2,3,4)
        available_today = vehicle_ids[:5]
        for v_id in available_today:
            cursor.execute("""
                INSERT INTO inventory_cal (vehicle_id, start_date, end_date, available_units)
                VALUES (%s, %s, %s, %s)
            """, (v_id, today, today, 1))
        
        # Tomorrow: 3 vehicles available (vehicle_ids 0,1,2)
        tomorrow = today + timedelta(days=1)
        available_tomorrow = vehicle_ids[:3]
        for v_id in available_tomorrow:
            cursor.execute("""
                INSERT INTO inventory_cal (vehicle_id, start_date, end_date, available_units)
                VALUES (%s, %s, %s, %s)
            """, (v_id, tomorrow, tomorrow, 1))
        
        # Day after tomorrow: 5 vehicles available (vehicle_ids 0,1,2,3,4)
        day_after_tomorrow = today + timedelta(days=2)
        available_day_after = vehicle_ids[:5]
        for v_id in available_day_after:
            cursor.execute("""
                INSERT INTO inventory_cal (vehicle_id, start_date, end_date, available_units)
                VALUES (%s, %s, %s, %s)
            """, (v_id, day_after_tomorrow, day_after_tomorrow, 1))
        
        # Day 4: 2 vehicles available (vehicle_ids 0,1)
        day_4 = today + timedelta(days=3)
        available_day_4 = vehicle_ids[:2]
        for v_id in available_day_4:
            cursor.execute("""
                INSERT INTO inventory_cal (vehicle_id, start_date, end_date, available_units)
                VALUES (%s, %s, %s, %s)
            """, (v_id, day_4, day_4, 1))
        
        # Days 5-30: All 7 vehicles available
        for day_offset in range(4, 31):
            date = today + timedelta(days=day_offset)
            for v_id in vehicle_ids:
                cursor.execute("""
                    INSERT INTO inventory_cal (vehicle_id, start_date, end_date, available_units)
                    VALUES (%s, %s, %s, %s)
                """, (v_id, date, date, 1))
        
        
        conn.commit()
        print("Successfully inserted sample data!")
        print(f"Total vehicles: {len(vehicle_ids)}")
        print(f"Today ({today}): 5 vehicles available")
        print(f"Tomorrow ({tomorrow}): 3 vehicles available") 
        print(f"Day after tomorrow ({day_after_tomorrow}): 5 vehicles available")
        print(f"Day 4 ({day_4}): 2 vehicles available")
        print("Days 5-30: All 7 vehicles available")
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    insert_sample_data()