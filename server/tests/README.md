# Tests

Start the dedicated test database (separate from the dev DB, port 5436) before running pytest:

```bash
docker compose -f tests/docker-compose.yml up -d
```

Then, from `server/`:

```bash
pytest -v
```
