import mysql.connector
from config import DB_CONFIG

def initialize_database():
    try:
        # Connect to MySQL server 
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = conn.cursor()

        # Create database if not exists
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        print(f"Database '{DB_CONFIG['database']}' created or already exists")

        # Switch to the database
        cursor.execute(f"USE {DB_CONFIG['database']}")
        
        # Execute schema SQL
        schema_sql = """
            drop database if exists ecoviadrive;
            CREATE DATABASE ecoviadrive;
            USE ecoviadrive;

            /* Stores Moroccan cities or regions where partners operate (e.g., Essaouira, Marrakech) */
            CREATE TABLE city (
            city_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            region VARCHAR(100)
            );

            /* Stores business partners such as hotels or car rental agencies */
            -- Flags indicate if the partner is a hotel or a rental agency
            CREATE TABLE partner (
            partner_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            city_id INT NOT NULL,
            contact_email VARCHAR(150),
            contact_phone VARCHAR(50),
            hotel_flag TINYINT(1) DEFAULT 0,
            rental_agency_flag TINYINT(1) DEFAULT 0,
            created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (city_id) REFERENCES city(city_id)
            );

            /* Stores customer information who rent cars (includes ID type and nationality) */
            CREATE TABLE customer (
            customer_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            email VARCHAR(150) NOT NULL,
            phone VARCHAR(50),
            nationality VARCHAR(100),
            id_type ENUM('PASSPORT','CIN','OTHER') NOT NULL,
            id_number VARCHAR(100),
            created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            /* Stores identity documents uploaded by customers for verification */
            CREATE TABLE document (
            doc_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            customer_id BIGINT NOT NULL,
            doc_type ENUM('PASSPORT','CIN','DRIVERS_LICENSE','OTHER') NOT NULL,
            doc_uri VARCHAR(255), -- URI or file path to the uploaded document (e.g., scan or photo of ID)
            verified_flag TINYINT(1) DEFAULT 0, -- Flag indicating if the document is verified (0 = not verified, 1 = verified)
            uploaded_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
            );

            /* Stores the classification of vehicles (number of seats, fuel type, transmission, etc.) */
            CREATE TABLE vehicle_class (
            class_id INT AUTO_INCREMENT PRIMARY KEY,
            label VARCHAR(50) NOT NULL,
            seats TINYINT,
            transmission ENUM('MANUAL','AUTO','OTHER'),
            fuel_type ENUM('GASOLINE','DIESEL','HYBRID','ELECTRIC','OTHER')
            );

            /* Stores each individual car available for rent */
            CREATE TABLE vehicle (
            vehicle_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            partner_id INT NOT NULL,
            class_id INT NOT NULL,
            reg_plate VARCHAR(50),
            make VARCHAR(100),
            model VARCHAR(100),
            model_year SMALLINT,
            img_uri VARCHAR(255),
            active_flag TINYINT(1) DEFAULT 1,
            FOREIGN KEY (partner_id) REFERENCES partner(partner_id),
            FOREIGN KEY (class_id) REFERENCES vehicle_class(class_id)
            );

            /* Stores rate plans for vehicles (e.g., daily price, currency, deposit, policy) */
            CREATE TABLE rate_plan (
            rate_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            vehicle_id BIGINT NOT NULL,
            daily_rate DECIMAL(10,2) NOT NULL,
            currency CHAR(3) DEFAULT 'MAD',
            deposit_required DECIMAL(10,2),
            cancellation_policy VARCHAR(255),
            start_date DATE,
            end_date DATE,
            FOREIGN KEY (vehicle_id) REFERENCES vehicle(vehicle_id)
            );

            /* Stores the availability calendar for each vehicle */
            CREATE TABLE inventory_cal (
            inv_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            vehicle_id BIGINT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            available_units INT DEFAULT 1,
            FOREIGN KEY (vehicle_id) REFERENCES vehicle(vehicle_id)
            );

            /* Stores customer bookings for vehicles */
            CREATE TABLE booking (
            booking_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            customer_id BIGINT NOT NULL,
            vehicle_id BIGINT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            total_price DECIMAL(10,2),
            currency CHAR(3) DEFAULT 'MAD',
            source_channel ENUM('DIRECT','BOOKING_COM','AIRBNB','OTHER') DEFAULT 'DIRECT',
            payment_status ENUM('UNPAID','PAID','REFUNDED','PARTIAL') DEFAULT 'UNPAID',
            booking_status ENUM('PENDING','CONFIRMING','CONFIRMED','REJECTED','CANCELLED') DEFAULT 'PENDING',
            created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
            FOREIGN KEY (vehicle_id) REFERENCES vehicle(vehicle_id)
            );

            /* Stores payment details for bookings */
            CREATE TABLE payment (
            payment_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            booking_id BIGINT NOT NULL,
            gateway VARCHAR(50),
            amount DECIMAL(10,2) NOT NULL,
            currency CHAR(3) DEFAULT 'MAD',
            paid_ts TIMESTAMP NULL,
            txn_ref VARCHAR(100), -- Reference ID from the payment gateway for the transaction
            FOREIGN KEY (booking_id) REFERENCES booking(booking_id)
            );

            /* Stores blacklisted customers who are banned from future rentals */
            CREATE TABLE blacklist (
            black_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            customer_id BIGINT NOT NULL,
            reason VARCHAR(255),
            active_flag TINYINT(1) DEFAULT 1,
            created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
            );

            /* Stores CSR donations made through bookings for stray or sick animals */
            CREATE TABLE csr_donation (
            csr_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            booking_id BIGINT NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            beneficiary_desc VARCHAR(255), -- A description of the beneficiary who receives the donation (e.g., “Stray dog shelter” or “Sick animal care”).
            created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (booking_id) REFERENCES booking(booking_id)
            );


            /* Stores admin users (e.g., staff who manage bookings or vehicles) */
            CREATE TABLE admin_user (
            admin_id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            email VARCHAR(150) NOT NULL UNIQUE,
            role ENUM('ADMIN','MANAGER','STAFF') DEFAULT 'STAFF',
            password_hash VARCHAR(255) NOT NULL,
            created_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            /* Stores vehicle maintenance history */
            CREATE TABLE maintenance (
            maintenance_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            vehicle_id BIGINT NOT NULL,
            description TEXT,
            maintenance_date DATE,
            cost DECIMAL(10,2),
            FOREIGN KEY (vehicle_id) REFERENCES vehicle(vehicle_id)
            );

            /* Stores promotional discount codes */
            CREATE TABLE promo (
            promo_code VARCHAR(20) PRIMARY KEY,
            discount_percent TINYINT NOT NULL CHECK (discount_percent BETWEEN 1 AND 100),
            start_date DATE NOT NULL,
            end_date DATE NOT NULL
            );

            /* Stores customer reviews and ratings for vehicles */
            CREATE TABLE review (
            review_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            customer_id BIGINT NOT NULL,
            vehicle_id BIGINT NOT NULL,
            rating TINYINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
            comment TEXT,
            review_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
            FOREIGN KEY (vehicle_id) REFERENCES vehicle(vehicle_id)
            );

            /* Stores contracts signed with partner hotels or agencies */
            CREATE TABLE contract (
            contract_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            partner_id INT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE,
            terms_pdf_uri VARCHAR(255),
            signed_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (partner_id) REFERENCES partner(partner_id)
            );

        """
        
        # Execute each statement separately
        for statement in schema_sql.split(';'):
            if statement.strip():
                cursor.execute(statement)
        
        conn.commit()
        print("All tables created successfully!")
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    initialize_database()