import os
from dotenv import load_dotenv
import psycopg2
import logging

load_dotenv()

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')

logging.basicConfig(level=logging.INFO)

# Function to create the 'attendance' table
def create_attendance_table():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST
    )
    cursor = conn.cursor()

    create_table_query = '''
        CREATE TABLE IF NOT EXISTS attendance (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT NOT NULL,
            nickname VARCHAR(255) NOT NULL,
            enter_time VARCHAR(50) NOT NULL,
            exit_time VARCHAR(50),
            enter_location_nickname VARCHAR(255) NOT NULL,
            exit_location_nickname VARCHAR(255)
        );
    '''

    cursor.execute(create_table_query)
    conn.commit()

    cursor.close()
    conn.close()

# Function to create the 'allowed_locations' table
def create_allowed_locations_table():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST
    )
    cursor = conn.cursor()

    create_table_query = '''
        CREATE TABLE IF NOT EXISTS allowed_locations (
            id SERIAL PRIMARY KEY,
            location_nickname VARCHAR(255) NOT NULL,
            latitude FLOAT NOT NULL,
            longitude FLOAT NOT NULL
        );
    '''

    cursor.execute(create_table_query)
    conn.commit()

    cursor.close()
    conn.close()

if __name__ == '__main__':
    create_attendance_table()
#    create_allowed_locations_table()

