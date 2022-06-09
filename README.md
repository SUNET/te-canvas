# te-canvas

## Quick start

Export the following env vars:

```
TE_ID
TE_USERGROUP

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

MAX_WORKERS*

* Predefined in docker-compose file
```

Start PostgreSQL:

```
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up postgres
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

Export the following env vars:

```
TE_ID
TE_USERGROUP

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

MAX_WORKERS*

TAG_API*
TAG_SYNC*

* Predefined in docker-compose file
```

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

The two previous commands are written down in `start-prod.sh` and `start-dev.sh` for convenience.

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
│   ├── start-prod.sh      -> ../te-canvas/start-prod.sh     
│   └── .env
└── back-2
    ├── docker-compose.yml -> ../te-canvas/docker-compose.yml
    ├── start-prod.sh      -> ../te-canvas/start-prod.sh     
    └── .env
```

The front end will access back end services using container names, e.g. `back-1_api_1`.

## Testing

```
docker-compose --profile test up
./test.sh
```

The following setup is required for tests which interact with TimeEdit and Canvas. Note that tests which interact with TimeEdit will probably not work (at the time of writing) with a TimeEdit instance other than the particular one used during development.

Canvas course:

- Id: `169` (edit in `te_canvas/test/common.py` as needed)

TimeEdit object:

- Type: `Lokal (Hel)`
- Ext. id: `fullroom_unittest`
- Id: `unittest`
- Name: `Unit Test Room`

TimeEdit reservation:

- Room: `unittest`
- Start at: `2022-10-01, 12:00`
- End at: `2022-10-01, 13:00`
