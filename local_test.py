import os
from dotenv import load_dotenv
from handler import lambda_handler

# Load environment variables from .env file
load_dotenv()

# Test the Lambda handler locally
if __name__ == "__main__":
    result = lambda_handler(None, None)
    print(result)