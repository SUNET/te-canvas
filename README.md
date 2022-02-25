# te-canvas

## Quick start

Export the following env vars:

```
TE_WSDL_URL
TE_CERT
TE_USERNAME
TE_PASSWORD

CANVAS_URL
CANVAS_KEY

TE_CANVAS_URL
TE_CANVAS_DB_HOSTNAME
TE_CANVAS_DB_PORT
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_DB
```

Start PostgreSQL:

```
docker-compose up -d
```

Install the requirements:

```
pip install -r requirements/dev.txt
```

Start dev server:

```
python -m te_canvas.main
```
