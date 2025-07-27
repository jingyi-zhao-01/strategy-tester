import asyncio
import json
import sys
import os
import subprocess

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'options'))

# Import the main function from options/main.py
from options.main import main
from options.operations import db

async def setup_database():
    """
    Set up the database by running Prisma migrations.
    """
    try:
        # Connect to the database
        await db.connect()
        
        # Create tables if they don't exist - execute each statement separately
        await db.query_raw("""
        CREATE TABLE IF NOT EXISTS public.options (
            id SERIAL PRIMARY KEY,
            ticker TEXT UNIQUE NOT NULL,
            underlying_ticker TEXT NOT NULL,
            contract_type TEXT NOT NULL,
            expiration_date TIMESTAMPTZ NOT NULL,
            strike_price FLOAT NOT NULL
        )
        """)
        
        await db.query_raw("""
        CREATE INDEX IF NOT EXISTS options_underlying_ticker_expiration_date_idx 
        ON public.options(underlying_ticker, expiration_date)
        """)
        
        await db.query_raw("""
        CREATE INDEX IF NOT EXISTS options_strike_price_idx 
        ON public.options(strike_price)
        """)
        
        await db.query_raw("""
        CREATE TABLE IF NOT EXISTS public.option_snapshots (
            id SERIAL PRIMARY KEY,
            ticker TEXT NOT NULL,
            volume FLOAT,
            day_change FLOAT,
            day_close FLOAT,
            day_open FLOAT,
            implied_vol FLOAT,
            last_price FLOAT,
            last_updated TIMESTAMPTZ,
            last_crawled TIMESTAMPTZ NOT NULL,
            open_interest INTEGER,
            FOREIGN KEY (ticker) REFERENCES public.options(ticker)
        )
        """)
        
        await db.query_raw("""
        CREATE UNIQUE INDEX IF NOT EXISTS option_snapshots_ticker_last_updated_idx 
        ON public.option_snapshots(ticker, last_updated)
        """)
        
        print("Database setup completed successfully")
    except Exception as e:
        print(f"Error setting up database: {e}")
        raise
    finally:
        # Disconnect from the database
        await db.disconnect()

async def run_main_with_setup():
    """
    Run the setup and main functions in sequence.
    """
    await setup_database()
    await main()

def lambda_handler(event, context):
    """
    AWS Lambda handler function that runs the main async function.
    
    Args:
        event: AWS Lambda event
        context: AWS Lambda context
        
    Returns:
        dict: Response with status code and message
    """
    try:
        # Run the setup and main async functions
        asyncio.run(run_main_with_setup())
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Options processing completed successfully'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

if __name__ == "__main__":
    # For local testing
    lambda_handler(None, None)