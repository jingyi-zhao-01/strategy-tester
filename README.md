# Strategy Tester Lambda Function

This project sets up a Lambda function to run the options strategy tester on a schedule.

## Environment Variables

The following environment variables are required:

- `DATABASE_URL`: PostgreSQL connection string
- `POLYGON_API_KEY`: API key for Polygon.io

## Local Development

### Prerequisites

- Node.js and npm
- Python 3.9+
- PostgreSQL database

### Setup

1. Install dependencies:

```bash
npm install
pip install -r requirements.txt
```

2. Generate Prisma client:

```bash
cd options
prisma generate
```

3. Run locally:

```bash
npm run local
```

## Deployment

### Using Serverless Framework

1. Configure AWS credentials:

```bash
aws configure
```

2. Deploy to AWS:

```bash
serverless deploy
```

## Project Structure

- `handler.py`: Lambda function handler
- `options/`: Main application code
- `serverless.yml`: Serverless Framework configuration
- `local_test.py`: Script for local testing

## Database Schema

The application uses two main tables:

1. `options`: Stores option contract details
2. `option_snapshots`: Stores snapshots of option data over time

## Schedule

By default, the Lambda function runs once per day to fetch and process options data.