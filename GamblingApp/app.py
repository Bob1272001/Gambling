from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from psycopg import connect
import os
import logging
import time
import threading
import pytz
import asyncio
from statbotics import Statbotics

app = FastAPI()

# Mount the static directory to serve CSS, JavaScript, and HTML files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
EVENT_ID = "2024casj"  # Replace with your desired event ID

# Statbotics instance
sb = Statbotics()

# Current time variable (Global)
currentTime = time.strftime("%Y-%m-%d %H:%M:%S")
est = pytz.timezone('America/New_York')

# Event to handle graceful shutdown of the time updating thread
shutdown_event = threading.Event()

# Update time function
def updateTime():
    global currentTime
    while not shutdown_event.is_set():  # Run until shutdown event is triggered
        currentTime = time.strftime("%Y-%m-%d %H:%M:%S")
        time.sleep(1)

# Start the time updating thread
thread = threading.Thread(target=updateTime, daemon=True)
thread.start()

# Handle graceful shutdown of the thread using FastAPI lifecycle events
@app.on_event("shutdown")
def shutdown_event_handler():
    logger.info("Shutdown event received. Stopping updateTime thread...")
    shutdown_event.set()
    thread.join()

# Background task to update upcoming matches every 30 seconds
async def update_upcoming_matches():
    while True:
        try:
            event_data = sb.get_event(EVENT_ID)
            matches = event_data.get('matches', [])

            conn = get_db_conn()
            with conn.cursor() as cur:
                for match in matches:
                    match_id = match['key']
                    event_id = match['event_key']
                    match_time = match['time']
                    teams = ", ".join([team for team in match['alliances']['red']['team_keys'] + match['alliances']['blue']['team_keys']])
                    
                    # Placeholder odds for each team, formatted as a string
                    red_team_odds = 1.5
                    blue_team_odds = 2.0
                    odds_string = f"{red_team_odds},{blue_team_odds}"

                    cur.execute('''
                        INSERT INTO "UpcomingMatches" ("MatchID", "EventID", "Time", "Teams", "Odds")
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT ("MatchID")
                        DO UPDATE SET "EventID" = EXCLUDED."EventID",
                                      "Time" = EXCLUDED."Time",
                                      "Teams" = EXCLUDED."Teams",
                                      "Odds" = EXCLUDED."Odds"
                    ''', (match_id, event_id, match_time, teams, odds_string))

                conn.commit()
        except Exception as e:
            logger.error(f"Error updating upcoming matches: {e}")
        finally:
            if conn:
                conn.close()

        await asyncio.sleep(30)  # Run every 30 seconds

# Register the background task with FastAPI
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(update_upcoming_matches())

# Serve the HTML file for the root endpoint
@app.get("/", response_class=HTMLResponse)
async def read_index():
    html_path = os.path.join("static", "index.html")
    return FileResponse(html_path)

# Database connection function
def get_db_conn():
    try:
        conn = connect(
            dbname="my_database",
            user="Thomas",
            password="Bob127227",
            host="localhost",
            port="5432"
        )
        conn.autocommit = False
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection error")

# API endpoint to get upcoming matches
@app.get("/api/upcoming_matches")
async def get_upcoming_matches():
    conn = None
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute('SELECT "MatchID", "Teams", "Time", "Odds" FROM "UpcomingMatches"')
            matches = cur.fetchall()

        return {"matches": matches}
    except Exception as e:
        logger.error(f"Error fetching upcoming matches: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        if conn:
            conn.close()

# API endpoint to place a bet
@app.post("/api/place_bet")
async def place_bet(request: Request):
    conn = None
    try:
        data = await request.json()
        username = data.get("Username")
        match_id = data.get("MatchID")
        amount = int(data.get("Amount"))
        team = data.get("Team")
        if team not in ['red', 'blue']:
            raise HTTPException(status_code=400, detail="Invalid team selection")
        
        if not username or not match_id or amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid input")

        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute('SELECT "ID", "Currency" FROM "Users" WHERE "Username" = %s', (username,))
            user = cur.fetchone()

            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            user_id, currency = user
            if amount > currency:
                raise HTTPException(status_code=400, detail="Insufficient currency")

            cur.execute('SELECT "Odds" FROM "UpcomingMatches" WHERE "MatchID" = %s', (match_id,))
            match = cur.fetchone()
            if not match:
                raise HTTPException(status_code=404, detail="Match not found")

            odds = match[0].split(",")
            selected_odds = float(odds[0]) if team == 'red' else float(odds[1])

            cur.execute('UPDATE "Users" SET "Currency" = %s WHERE "ID" = %s', (currency - amount, user_id))
            cur.execute('INSERT INTO "Bets" ("UserID", "MatchID", "Amount", "Odds", "Team") VALUES (%s, %s, %s, %s, %s)', 
                        (user_id, match_id, amount, selected_odds, team))

            conn.commit()

        return {"message": "Bet placed successfully"}
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error placing bet: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        if conn:
            conn.close()

# API endpoint to create a user
@app.post("/api/create_user")
async def create_user(request: Request):
    conn = None
    try:
        data = await request.json()
        logger.info(f"Received data for user creation: {data}")

        username = data.get("Username") or data.get("username")
        if not username:
            raise HTTPException(status_code=400, detail="Username is required")

        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute('INSERT INTO "Users" ("Username", "Currency") VALUES (%s, %s) RETURNING "ID"', (username, 1000))
            user_id = cur.fetchone()[0]
            conn.commit()

        return {"message": "User created successfully", "UserID": user_id}
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        if conn:
            conn.close()

# API endpoint to place a bet, it done broke but debug later
@app.post("/api/place_bet")
async def place_bet(request: Request):
    conn = None
    try:
        data = await request.json()
        username = data.get("Username")
        match_id = data.get("MatchID")
        amount = int(data.get("Amount"))
        odds = float(data.get("Odds"))

        if not username or not match_id or amount <= 0 or odds <= 0:
            raise HTTPException(status_code=400, detail="Invalid input")

        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute('SELECT "ID", "Currency" FROM "Users" WHERE "Username" = %s', (username,))
            user = cur.fetchone()

            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            user_id, currency = user
            if amount > currency:
                raise HTTPException(status_code=400, detail="Insufficient currency")

            cur.execute('UPDATE "Users" SET "Currency" = %s WHERE "ID" = %s', (currency - amount, user_id))
            cur.execute('INSERT INTO "Bets" ("UserID", "MatchID", "Amount", "Odds") VALUES (%s, %s, %s, %s)', 
                        (user_id, match_id, amount, odds))

            conn.commit()

        return {"message": "Bet placed successfully"}
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error placing bet: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        if conn:
            conn.close()

# API endpoint to get all users
@app.get("/api/get_users")
async def get_users():
    conn = None
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute('SELECT "Username", "Currency" FROM "Users"')
            users = cur.fetchall()

        return {"users": users}
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        if conn:
            conn.close()

# API endpoint to get all bets
@app.get("/api/get_bets")
async def get_bets():
    conn = None
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute('''
                SELECT u."Username", b."MatchID", b."Amount", b."Odds"
                FROM "Bets" b
                JOIN "Users" u ON b."UserID" = u."ID"
            ''')
            bets = cur.fetchall()

        return {"bets": bets}
    except Exception as e:
        logger.error(f"Error fetching all bets: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        if conn:
            conn.close()

# API endpoint to get bets of a specific user
@app.get("/api/get_user_bets")
async def get_user_bets(username: str):
    conn = None
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute('''
                SELECT b."MatchID", b."Amount", b."Odds"
                FROM "Bets" b
                JOIN "Users" u ON b."UserID" = u."ID"
                WHERE u."Username" = %s
            ''', (username,))
            bets = cur.fetchall()

        logger.info(f"Fetched bets for {username}: {bets}")
        return {"bets": bets}
    except Exception as e:
        logger.error(f"Error fetching bets for user {username}: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        if conn:
            conn.close()

# API endpoint to get a user's currency
@app.get("/api/get_user_currency")
async def get_user_currency(username: str):
    conn = None
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute('SELECT "Currency" FROM "Users" WHERE "Username" = %s', (username,))
            user = cur.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            currency = user[0]

        return {"currency": currency}
    except Exception as e:
        logger.error(f"Error fetching currency for user {username}: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        if conn:
            conn.close()

# API endpoint to end a bet and update user's currency
@app.post("/api/end_bet")
async def end_bet(request: Request):
    conn = None
    try:
        data = await request.json()
        username = data.get("Username")
        match_id = data.get("MatchID")

        if not username or not match_id:
            raise HTTPException(status_code=400, detail="Username and MatchID are required")

        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute('''
                SELECT b."Amount", b."Odds", u."ID", u."Currency"
                FROM "Bets" b
                JOIN "Users" u ON b."UserID" = u."ID"
                WHERE u."Username" = %s AND b."MatchID" = %s
            ''', (username, match_id))
            bet = cur.fetchone()

            if not bet:
                raise HTTPException(status_code=404, detail="Bet not found")

            amount, odds, user_id, current_currency = bet

            winnings = int(amount * odds)
            new_currency = current_currency + winnings

            cur.execute('UPDATE "Users" SET "Currency" = %s WHERE "ID" = %s', (new_currency, user_id))
            cur.execute('DELETE FROM "Bets" WHERE "UserID" = %s AND "MatchID" = %s', (user_id, match_id))

            conn.commit()

        return {"message": "Bet ended successfully"}
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error ending bet for user {username}: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        if conn:
            conn.close()
            
# Serve the HTML file for user creation page
@app.get("/create_user", response_class=HTMLResponse)
async def read_create_user():
    html_path = os.path.join("static", "create_user.html")
    return FileResponse(html_path)
