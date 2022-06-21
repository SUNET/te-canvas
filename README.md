# te-canvas

This README contains information on working with the back end code. For higher level project documentation, see [te-canvas/doc.md](https://github.com/SUNET/te-canvas/blob/main/doc.md).

The back end consists of two parts; a sync engine and an API server to control it. To run either you first need to define the environment variables listed under [Configuration](#configuration).

The main Docker compose file comes with an optional override file `docker-compose.dev.yml`, which exposes ports for all containers and builds images locally. This is convenient to use during development but not safe in production. To use `docker-compose.dev.yml` you need to specify both compose files explicitly using the `-f` flag (`-f docker-compose.yml -f docker-compose.dev.yml`).

## Run without Docker (not for production)

Start Postgres:

```
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up postgres
```

Install the requirements:

```
pip install -r requirements/dev.txt
```

Start API (Flask development server):

```
python -m te_canvas.api
```

Start sync engine:

```
python -m te_canvas.sync
```

## Run with Docker

Start API server (Gunicorn + Nginx):

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

Start in dev mode, with exposed ports (**not safe in production**) and using locally built images:

```
docker-compose -f docker-compose.yml -f docker-compose.dev.yml --profile <sync | api> up
```

The two previous commands are written down in `start-prod.sh` and `start-dev.sh` for convenience.

## Configuration

te-canvas is configured using the following environment variables.

| Environment variable | Description                                      | Predefined in docker-compose file? |
| -                    | -                                                | -                                  |
| `TE_ID`              | ID of TimeEdit instance. Find this e.g. in the URL `https://cloud.timeedit.net/<ID>/client/login`. | |
| `TE_USERGROUP`       | TimeEdit "user group" to be used in links to edit TimeEdit events. Find this by selecting a group with edit permissions at `https://cloud.timeedit.net/<ID>/web`. | |
| `TE_CERT`            | TimeEdit SOAP API certificate.                   |                                    |
| `TE_USERNAME`        | TimeEdit username.                               |                                    |
| `TE_PASSWORD`        | TimeEdit password.                               |                                    |
|                      |                                                  |                                    |
| `CANVAS_URL`         | URL of Canvas instance.                          |                                    |
| `CANVAS_KEY`         | Canvas API key.                                  |                                    |
|                      |                                                  |                                    |
| `POSTGRES_HOSTNAME`  | Postgres hostname.                               | ✅                                 |
| `POSTGRES_PORT`      | Postgres port.                                   | ✅                                 |
| `POSTGRES_DB`        | Name of database.                                | ✅                                 |
| `POSTGRES_USER`      | Postgres username.                               | ✅                                 |
| `POSTGRES_PASSWORD`  | Postgres password.                               |                                    |
|                      |                                                  |                                    |
| `MAX_WORKERS`        | Number of threads to use. 1 = fully sequential.  | ✅                                 |
| `TAG_API`            | Tag to use for `docker.sunet.se/te-canvas-api`.  | ✅                                 |
| `TAG_SYNC`           | Tag to use for `docker.sunet.se/te-canvas-sync`. | ✅                                 |

Dynamic config is set using the `/api/config` endpoint, which exposes a simple key-value store. This is used only for [event template](https://github.com/SUNET/te-canvas/blob/main/doc.md#event-template) strings.

## Testing

```
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
