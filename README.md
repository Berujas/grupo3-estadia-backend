
Backend

## Stack backend (tools/frameworks)
- API: FastAPI + Uvicorn
- ORM/Migraciones: SQLAlchemy + Alembic
- Cache/Colas: Redis
- Base de datos: PostgreSQL
- ETL: Python (pandas, openpyxl, pyarrow) + SQLAlchemy
- Config: pydantic-settings (.env)
- Auth (estándar): JWT (python-jose) + passlib[bcrypt]
- Infra local: Docker Compose
- Calidad: black, isort, flake8, pre-commit, pytest
- CI: GitHub Actions
eof
