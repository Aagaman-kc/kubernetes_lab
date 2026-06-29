from fastapi import FastAPI
import psycopg2
import os

app = FastAPI()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT", "5432")
)
@app.get("/")
def get_users():

    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users")

    rows = cursor.fetchall()

    cursor.close()

    return {
        "users": rows
    }