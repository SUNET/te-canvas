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

POSTGRES_HOSTNAME*
POSTGRES_PORT*
POSTGRES_DB*
POSTGRES_USER*
POSTGRES_PASSWORD

EVENT_TITLE
EVENT_LOCATION
EVENT_DESCRIPTION

* Predifined in docker-compose file
```

Start PostgreSQL:

```
docker-compose up postgres
```

Install the requirements:

```
pip install -r requirements/dev.txt
```

Start API dev server:

```
python -m te_canvas.api
```

Start sync engine:

```
python -m te_canvas.sync
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

## Docker

Start API server:

```
docker-compose --profile api up
```

Start sync engine:

```
docker-compose --profile sync up
```

Start both:

```
docker-compose --profile api --profile sync up
```

To start Docker in production mode, without exposed ports and using prebuilt images:

```
docker-compose -f docker-compose.yml --profile <sync | api> up
```

## Testing

```
docker-compose --profile test up
./test.sh
```
