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

To start in dev mode, with exposed ports (*not safe in production*) and using locally built images:

```
docker-compose -f docker-compose.yml -f docker-compose.dev.yml --profile <sync | api> up
```

## Testing

```
docker-compose --profile test up
./test.sh
```

## Suggested complete project setup

```
.
├── te-canvas       [repo]
├── te-canvas-front [repo]
├── front
│   ├── docker-compose.yml -> ../te-canvas-front/docker-compose.yml
│   ├── lti.json           -> ../te-canvas-front/lti.json
│   ├── nginx-docker.conf  -> ../te-canvas-front/nginx-docker.conf
│   ├── ssl.crt            -> /etc/letsencrypt/live/my-domain.com/fullchain.pem
│   ├── ssl.key            -> /etc/letsencrypt/live/my-domain.com/privkey.pem
│   ├── .env
│   └── platforms.json
├── back-1
│   ├── docker-compose.yml -> ../te-canvas/docker-compose.yml
│   └── .env
└── back-2
    ├── docker-compose.yml -> ../te-canvas/docker-compose.yml
    └── .env
```

The front end will access back end services using container names, e.g. `back-1_api_1`.
