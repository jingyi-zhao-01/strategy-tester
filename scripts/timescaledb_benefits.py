import os
import datetime
import time
import psycopg2
from psycopg2.extras import RealDictCursor

def run_query(cursor, query, params=None, description=None):
    """Run a query and measure its execution time"""
    if description:
        print(f"\n{description}")
    
    start_time = time.time()
    cursor.execute(query, params)
    results = cursor.fetchall()
    end_time = time.time()
    
    print(f"Query executed in {(end_time - start_time) * 1000:.2f} ms")
    print(f"Number of results: {len(results)}")
    
    # Print first few results
    if results and len(results) > 0:
        print("Sample results:")
        for row in results[:3]:
            print(f"  {row}")
    
    return results

def main():
    # Connect to the database
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    print("Connected to database")
    
    # Get current time for queries
    now = datetime.datetime.now(datetime.timezone.utc)
    one_week_ago = now - datetime.timedelta(days=7)
    
    # 1. Demonstrate time-bucket aggregation (TimescaleDB specific)
    run_query(
        cursor,
        """
        SELECT 
            time_bucket('1 day', last_updated) AS day,
            "optionId",
            AVG(last_price) AS avg_price,
            MIN(last_price) AS min_price,
            MAX(last_price) AS max_price,
            SUM(volume) AS total_volume
        FROM option_snapshots
        WHERE last_updated >= %s
        GROUP BY day, "optionId"
        ORDER BY day DESC, "optionId"
        LIMIT 10
        """,
        (one_week_ago,),
        "1. Time-bucket daily aggregation (TimescaleDB specific)"
    )
    
    # 2. Demonstrate time-bucket with different intervals
    run_query(
        cursor,
        """
        SELECT 
            time_bucket('1 hour', last_updated) AS hour,
            AVG(last_price) AS avg_price,
            COUNT(*) AS num_snapshots
        FROM option_snapshots
        WHERE last_updated >= %s
        GROUP BY hour
        ORDER BY hour DESC
        LIMIT 10
        """,
        (one_week_ago,),
        "2. Hourly time-bucket aggregation"
    )
    
    # 3. Demonstrate first/last value in each bucket
    run_query(
        cursor,
        """
        SELECT 
            time_bucket('1 day', last_updated) AS day,
            "optionId",
            first(last_price, last_updated) AS open_price,
            last(last_price, last_updated) AS close_price
        FROM option_snapshots
        WHERE last_updated >= %s
        GROUP BY day, "optionId"
        ORDER BY day DESC, "optionId"
        LIMIT 10
        """,
        (one_week_ago,),
        "3. First/last value in each time bucket (open/close prices)"
    )
    
    # 4. Demonstrate continuous aggregates (if available)
    try:
        run_query(
            cursor,
            """
            SELECT * FROM hypertable_detailed_size('option_snapshots');
            """,
            None,
            "4. Hypertable size information"
        )
    except Exception as e:
        print(f"\n4. Hypertable size information")
        print(f"Error: {e}")
    
    # 5. Demonstrate compression benefits (if available)
    try:
        run_query(
            cursor,
            """
            SELECT * FROM chunk_compression_stats('option_snapshots');
            """,
            None,
            "5. Compression statistics (if compression is enabled)"
        )
    except Exception as e:
        print(f"\n5. Compression statistics")
        print(f"Error: {e}")
    
    # Close the connection
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()