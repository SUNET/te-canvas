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

EVENT_TITLE
EVENT_LOCATION
EVENT_DESCRIPTION
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

## Configuration

The env vars `EVENT_TITLE`, `EVENT_LOCATION`, and `EVENT_DESCRIPTION` control how calendar events are translated from TimeEdit to Canvas. Each should be set to a string which may contain references to TimeEdit *object types* and their *fields* on the format `${type::field}`.

For example,

`EVENT_TITLE = '${activity::name} by ${teacher::firstname} ${teacher::lastname}'`

and a TimeEdit reservation with the objects

```
activity = { name: 'Lecture' },
teacher = { firstname: 'Ernst', lastname: 'Widerberg' }
```

will create a Canvas event titled *Lecture by Ernst Widerberg*.
