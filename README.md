# te-canvas

This README contains information on working with the back end code. For higher level project documentation, see [te-canvas/doc.md](https://github.com/SUNET/te-canvas/blob/main/doc.md).

The back end consists of two parts; a sync engine and an API server to control it. To run either you first need to define the environment variables listed under [Configuration](#configuration).

## Docker compose version

We're using docker-compose specification **V1**.  
docker-compose version **1.29.2** is recommened.  
The extended shell style features used in docker-compose.yml might not be supported on older versions of docker-compose.

## Python version

We use features added to Python after **3.8.10**.

## Run without Docker (not for production)

Start Postgres:

```
docker-compose up postgres
```

Install the requirements:

```
pip install -r requirements/dev.txt
```

Start API server (Flask development server):

```
python -m te_canvas.api
```

Start sync engine:

```
python -m te_canvas.sync
```

## Run with Docker

> The main Docker compose file comes with an [override](https://docs.docker.com/compose/extends/) file, which exposes ports for all containers and builds images locally. This is convenient to use during development but not safe in production. **Note that `docker-compose.override.yml` is enabled by default** and simply doing `docker-compose up` in this repo will start in **unsafe dev mode**.
>
> To use _only_ the production-ready `docker-compose.yml`, you can do `docker-compose -f docker-compose.yml up`. But since we use Puppet for all this anyway, `docker-compose.override.yml` should never be near our production environment.

Start Postgres, API server (Gunicorn + Nginx), and sync engine:

```
docker-compose -f docker-compose.yml up
```

Start in dev mode, with exposed ports (**not safe in production**) and using locally built images:

```
docker-compose up
```

## Configuration

te-canvas is configured using the following environment variables.

| Environment variable | Description                                                                                                                                                                                                                                                                             | Predefined in docker-compose file? |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| `TE_ID`              | ID of TimeEdit instance. Find this e.g. in the URL `https://cloud.timeedit.net/<ID>/client/login`.                                                                                                                                                                                      |                                    |
| `TE_USERGROUP`       | TimeEdit "user group" to be used in links to edit TimeEdit events. Find this by selecting a group with edit permissions at `https://cloud.timeedit.net/<ID>/web`.                                                                                                                       |                                    |
| `TE_CERT`            | TimeEdit SOAP API certificate.                                                                                                                                                                                                                                                          |                                    |
| `TE_USERNAME`        | TimeEdit username.                                                                                                                                                                                                                                                                      |                                    |
| `TE_PASSWORD`        | TimeEdit password.                                                                                                                                                                                                                                                                      |                                    |
| `TE_SEARCH_FIELDS`   | Comma separated list of fields used when searching for TimeEdit objects. Defaults to `general.id,general.title` since that is very common. This variable is needed since the fields does not have the same name across TimeEdit instances.                                              | ✅                                 |
| `TE_RETURN_FIELDS`   | Comma separated list of fields used when searching for TimeEdit objects. Defaults to `general.id,general.title` since that is very common. This variable is needed since the first field is used by TimeEdit to sort the returned resources. Because of that, it needs to be mandatory. | ✅                                 |
| `CANVAS_URL`         | URL of Canvas instance.                                                                                                                                                                                                                                                                 |                                    |
| `CANVAS_KEY`         | Canvas API key.                                                                                                                                                                                                                                                                         |                                    |
| `POSTGRES_HOSTNAME`  | Postgres hostname.                                                                                                                                                                                                                                                                      | ✅                                 |
| `POSTGRES_PORT`      | Postgres port.                                                                                                                                                                                                                                                                          | ✅                                 |
| `POSTGRES_DB`        | Name of database.                                                                                                                                                                                                                                                                       | ✅                                 |
| `POSTGRES_USER`      | Postgres username.                                                                                                                                                                                                                                                                      | ✅                                 |
| `POSTGRES_PASSWORD`  | Postgres password.                                                                                                                                                                                                                                                                      |                                    |
|                      |                                                                                                                                                                                                                                                                                         |                                    |
| `MAX_WORKERS`        | Number of threads to use. 1 = fully sequential.                                                                                                                                                                                                                                         | ✅                                 |
| `TAG_API`            | Tag to use for `docker.sunet.se/te-canvas-api`.                                                                                                                                                                                                                                         | ✅                                 |
| `TAG_SYNC`           | Tag to use for `docker.sunet.se/te-canvas-sync`.                                                                                                                                                                                                                                        | ✅                                 |

Further configuration can be done from Canvas using the `/api/config` endpoint. The endpoint can be used to check if there's a valid _Event Template_. If not, syncing is suspended. It can also be used to create event templates on course and global level. Finally you can filter which TimeEdit _Object Types_ will show up when creating Sync Object connections. More information is available on [te-canvas-front](https://github.com/SUNET/te-canvas/blob/main/canvas-admin.md).

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

## Dockerfiles and CI

In the repo root we have two Dockerfiles `Dockerfile_api` and `Dockerfile_sync`. These are used when building locally.

There are also two directories `docker-api` and `docker-sync` which contain additional Dockerfiles. These are used for CI builds. This is a workaround for the fact that you can't (currently) specify a Dockerfile to the Jenkins job which starts our CI builds. So we must instead use separate contexts (directories) for API and sync respectively. This also requires us to clone the code instead of copying, since the code is in a parent dir of our context!

