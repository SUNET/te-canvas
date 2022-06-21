# Architecture overview

Each platform (Canvas instance) has its own API server. In front of this they all share one single LTI server. The JWTs which accompany browser requests contain information about their source platform. The LTI server uses this information to determine which API server to forward incoming requests to.

```
┌─────────┐                              ┌────────┐
│ Browser ├─────────────────────────────►│ Canvas │
│         │                              └───┬────┘
│         │                                  │
│         │                                  │
│         │                                  │ LTI handshake
│         │                                  │
│         │                                  │
│         │                                  ▼
│         │                        ┌───────────────────────┐                   ┌───────────────────────┐
│         │                        │ LTI server            │                   │ API server (Flask)    │
│         │                        │ (Express, Nginx)      │                   │                       │
│         │                        │                       │                   │ No own auth, trust    │
│         │                        │                       │                   │ all requests          │
│         │                        │                       │                   │ implicitly            │
│         │                        │                       │                   │                       │
│         │                        │                       │                   │ So, only reachable    │
│         │    React app + JWT     │                       │                   │ from LTI server       │
│         │◄───────────────────────┤                       │                   │                       │
│         │                        │                       │                   │                       │
│         │                        │                       │                   │                       │
│         │                        │                       │ Deciding which    │                       │
│         │                        │                       │ back end to       │                       │
│         │ Fetch request with JWT │                       │ forward to using  │                       │
│         │ as auth header         │                       │ JWT               │                       │
│         ├───────────────────────►│ As reverse proxy with ├──────────────────►│                       │
│         │                        │ "LTI termination"     │                   │                       │
│         │                        │ (JWT verification     │                   │                       │
│         │                        │ etc)                  │                   │                       │
│         │                        │                       │                   │                       │
│         │                        │                       │                   │                       │
│         │◄───────────────────────┤◄──────────────────────│◄──────────────────┤                       │
│         │                        │                       │                   │                       │
│         │                        │                       │                   │                       │
└─────────┘                        └───────────────────────┘                   └───────────────────────┘

                                                                               ┌───────────────────────┐
                                                                               │ API server 2          │
                                                                               │                       │
                                                                               │                       │
                                                                               └───────────────────────┘
                                                                                          ·
                                                                                          ·
                                                                                          ·
                                                                               ┌───────────────────────┐
                                                                               │ API server <n>        │
                                                                               │                       │
                                                                               │                       │
                                                                               └───────────────────────┘
```

# Suggested setup

This is an easy way you might set up both front and back end to run in Docker containers. The front end will access back end services using container names, e.g. `back-1_api_1` (configure this in [platforms.json](https://github.com/SUNET/te-canvas-front#platformsjson)).

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

# Terminology

In TimeEdit's data model each calendar event has a set of *objects* attached to it. Each object has a *type*, e.g. teacher, room, course, or course offering. `[1]`

On Canvas, an event belongs to a specific calendar. Calendars we are interested in are generally tied to a particular Canvas *course* but there are also calendars tied to *users* and *groups*.

In our code we have chosen to generalize the word for an "event container" as *group*. So on TimeEdit, a calendar is defined by a set of objects – we call each object a "group", since it contains a set of events. On Canvas, an event belongs to a *course* or *user* or *Canvas group* – likewise we call this entity in general a "group". This is a bit confusing since "group" as we use it is different from a Canvas group. At the time of writing we only support Canvas courses, but as explained we refer to them as "group" in the general form (sorry). tl;dr: If you see `canvas_group` in the code, you can mentally replace this with `canvas_course`.

We might also mention that TimeEdit calls items in a calendar "reservations", while Canvas refers to these as "events". We prefer to use "event" in our code.

`[1]`: Object types are different for each organization.

# Event template

The `/api/config` keys `title`, `location`, and `description` control how calendar events are translated from TimeEdit to Canvas. Each should be set to a string which may contain references to TimeEdit *object types* and their *fields* on the format `${type::field}`.

For example,

`title = '${activity::name} by ${teacher::firstname} ${teacher::lastname}'`

and a TimeEdit reservation with the objects

```
activity = { name: 'Lecture' },
teacher = { firstname: 'Ernst', lastname: 'Widerberg' }
```

will create a Canvas event titled *Lecture by Ernst Widerberg*.
