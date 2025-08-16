import os
import datetime
import random
import psycopg2
from psycopg2.extras import RealDictCursor
import re

def main():
    # Connect to the database
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.autocommit = True
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    print("Connected to database")
    
    # First, let's create some option records
    option_tickers = [
        "AAPL230721C00180000",
        "AAPL230721P00180000",
        "MSFT230721C00300000",
        "MSFT230721P00300000",
        "GOOG230721C02500000"
    ]
    
    options = []
    for ticker in option_tickers:
        # Use regex to parse the ticker format
        match = re.match(r'([A-Z]+)(\d{6})([CP])(\d+)', ticker)
        if match:
            underlying = match.group(1)
            exp_date_str = match.group(2)
            contract_type = "CALL" if match.group(3) == "C" else "PUT"
            strike_price = float(match.group(4)) / 1000
            
            # Parse the date
            exp_date = datetime.datetime.strptime(f"20{exp_date_str}", "%Y%m%d")
        else:
            print(f"Could not parse ticker: {ticker}")
            continue
        
        # Check if option exists
        cursor.execute(
            "SELECT * FROM options WHERE ticker = %s",
            (ticker,)
        )
        option = cursor.fetchone()
        
        if not option:
            # Create option record
            cursor.execute(
                """
                INSERT INTO options (ticker, underlying_ticker, contract_type, expiration_date, strike_price)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
                """,
                (ticker, underlying, contract_type, exp_date, strike_price)
            )
            option = cursor.fetchone()
            print(f"Created option: {option['ticker']} (ID: {option['id']})")
        else:
            print(f"Found option: {option['ticker']} (ID: {option['id']})")
        
        options.append(option)
    
    # Now create some snapshots (limited to 100 as requested)
    print("\nCreating option snapshots...")
    
    # Generate timestamps for the last 20 days
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamps = [now - datetime.timedelta(days=i) for i in range(20)]
    
    # Create snapshots for each option and timestamp (5 options * 20 days = 100 snapshots)
    snapshot_count = 0
    for option in options:
        for ts in timestamps:
            # Generate some random data
            price = option['strike_price'] * (0.8 + 0.4 * (ts.day % 10) / 10)
            
            # Create snapshot
            cursor.execute(
                """
                INSERT INTO option_snapshots (
                    id, "optionId", volume, day_change, day_close, day_open, 
                    implied_vol, last_price, last_updated, last_crawled, open_interest
                )
                VALUES (
                    nextval('option_snapshots_id_seq'), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (last_updated, "optionId", id) DO NOTHING
                """,
                (
                    option['id'],
                    1000 + (ts.day * 100),
                    0.5 - (ts.day % 10) / 10,
                    price,
                    price * 0.99,
                    0.3 + (ts.day % 10) / 100,
                    price,
                    ts,
                    now,
                    5000 + (ts.day * 200)
                )
            )
            snapshot_count += 1
            
    print(f"Created {snapshot_count} option snapshots")
    
    # Query to verify data
    print("\nVerifying data with a time-series query...")
    
    # Get snapshots for the first option over the last 7 days
    seven_days_ago = now - datetime.timedelta(days=7)
    cursor.execute(
        """
        SELECT * FROM option_snapshots
        WHERE "optionId" = %s AND last_updated >= %s
        ORDER BY last_updated DESC
        """,
        (options[0]['id'], seven_days_ago)
    )
    recent_snapshots = cursor.fetchall()
    
    print(f"Found {len(recent_snapshots)} recent snapshots for {options[0]['ticker']}")
    for snapshot in recent_snapshots[:5]:  # Show first 5
        print(f"  {snapshot['last_updated']}: Price = {snapshot['last_price']}, Volume = {snapshot['volume']}")
    
    # Run a TimescaleDB-specific query to demonstrate time-bucket functionality
    print("\nRunning a TimescaleDB time-bucket aggregation query:")
    cursor.execute(
        """
        SELECT 
            time_bucket('1 day', last_updated) AS bucket,
            "optionId",
            AVG(last_price) AS avg_price,
            MAX(last_price) AS max_price,
            MIN(last_price) AS min_price,
            SUM(volume) AS total_volume
        FROM option_snapshots
        GROUP BY bucket, "optionId"
        ORDER BY bucket DESC, "optionId"
        LIMIT 10
        """
    )
    aggregated_data = cursor.fetchall()
    
    print("Time-bucket aggregation results:")
    for row in aggregated_data:
        print(f"  {row['bucket']}: Option ID {row['optionId']}, Avg Price = {row['avg_price']:.2f}, Volume = {row['total_volume']}")
    
    # Close the connection
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()