from psycopg import connect


def test_db_connection():
    try:
        # Establish a connection to the database
        conn = connect(
            dbname="my_database",
            user="Thomas",
            password="Bob127227",
            host="localhost",
            port="5432"
        )
        print("Connection to database successful.")

        # Create a cursor object and execute a basic query
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            result = cur.fetchone()
            print(f"Query result: {result}")

    except Exception as e:
        print(f"Database connection error: {e}")

    finally:
        # Close the connection
        if conn:
            conn.close()

if __name__ == "__main__":
    test_db_connection()
