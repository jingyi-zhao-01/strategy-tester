# Strategy Tester - AWS SAM Migration

This project has been migrated from Serverless Framework to AWS SAM.

## Prerequisites

1. Install AWS SAM CLI:
   ```bash
   pip install aws-sam-cli
   ```

2. Configure AWS credentials:
   ```bash
   aws configure
   ```

## Development

### Build the application:
```bash
sam build
```

### Deploy the application:
```bash
# First deployment (guided)
sam deploy --guided

# Subsequent deployments
sam deploy
```

### Local testing:
```bash
# Start API Gateway locally
sam local start-api

# Invoke specific function
sam local invoke IngestOptionsFunction
sam local invoke IngestSnapshotsFunction
sam local invoke PingFunction
```

### View logs:
```bash
sam logs -n IngestOptionsFunction --tail
sam logs -n IngestSnapshotsFunction --tail
sam logs -n PingFunction --tail
```

## Configuration

1. Update `samconfig.toml` with your:
   - S3 bucket for deployments
   - Database URL
   - Polygon API key

2. Environment-specific configurations can be set via parameters in `template.yaml`

## API Endpoints

After deployment, your API will be available at:
- `GET /ping` - Health check
- `GET /process-options` - Ingest options contracts
- `GET /process-options-snapshot` - Ingest option snapshots

## Scheduled Functions

Both ingestion functions run daily via CloudWatch Events.

## Migration Notes

- Replaced `serverless.yml` with `template.yaml`
- Updated `.gitignore` to include SAM build artifacts
- Simplified `requirements.txt` (removed serverless-specific packages)
- Added `samconfig.toml` for deployment configuration
