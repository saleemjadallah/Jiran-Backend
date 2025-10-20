## Souk Loop Backend

FastAPI-based backend for the Souk Loop hyperlocal social commerce platform.

### Requirements
- Python 3.11+
- Docker & Docker Compose

### Local Development
1. Copy `.env.example` to `.env` and update values.
2. Install dependencies:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Run services with Docker Compose:
   ```bash
   docker compose up --build
   ```
4. API available at `http://localhost:8000`, docs at `/docs`.

### Running Alembic Migrations
```bash
alembic upgrade head
```

### Testing
```bash
pytest
```

### Deployment
- Build image: `docker build -t souk-loop-backend .`
- Configure environment variables for production before deploying.

