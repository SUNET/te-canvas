from datetime import datetime
import os
import sys

import zeep

from te_canvas.log import get_logger
from requests.exceptions import ConnectionError

logger = get_logger()

try:
    wsdl = os.environ["TE_WSDL_URL"]
    cert = os.environ["TE_CERT"]
    username = os.environ["TE_USERNAME"]
    password = os.environ["TE_PASSWORD"]
except Exception as e:
    logger.debug(f"Failed to load configuration: {e}, exiting.")
    sys.exit(-1)


try:
    client = zeep.Client(wsdl)
    key = client.service.register(cert).applicationkey
except Exception:
    logger.error(f'TimeEdit connection to "{wsdl}" failed, exiting.')
    sys.exit(-1)


def find_types_all():
    res = client.service.findTypes(
        login={
            "username": username,
            "password": password,
            "applicationkey": key,
        },
        ignorealias=False,
    )
    return { t["extid"]: t["name"] for t in res }


# TODO: Add returnFields parameter, populate from getAlFields?
def find_objects(type, number_of_objects, begin_index, search_string):
    """Get max 1000 objects of a given type."""
    resp = client.service.findObjects(
        login={
            "username": username,
            "password": password,
            "applicationkey": key,
        },
        type=type,
        numberofobjects=number_of_objects,
        beginindex=begin_index,
        generalsearchfields=["general.id"],
        generalsearchstring=search_string,
        returnfields=["general.id", "general.title"]
    )
    if resp.objects is None:
        return []
    return list(map(unpack_object, resp["objects"]["object"]))


def find_objects_all(type, search_string):
    """Get all objects of a given type."""
    n = client.service.findObjects(
        login={
            "username": username,
            "password": password,
            "applicationkey": key,
        },
        type=type,
        numberofobjects=1,
    ).totalnumberofobjects

    num_pages = -(-n // 1000)

    res = []
    for i in range(num_pages):
        page = find_objects(type, 1000, i * 1000, search_string)
        res += page
    return res


def unpack_object(o):
    res = {"extid": o["extid"]}
    for f in o["fields"]["field"]:
        res[f["extid"]] = f["value"][0]
    return res


def get_object(extid: str):
    """Get a specific object based on external id."""
    # NOTE: API says that this returns an array of objects, but only the first extid is used.
    resp = client.service.getObjects(
        login={
            "username": username,
            "password": password,
            "applicationkey": key,
        },
        objects=[extid]
    )
    res = list(map(unpack_object, resp))[0]
    print(res)
    types = find_types_all()
    type_id = res["extid"].split("_")[0] # NOTE: Assumption that external id is of form <type>_id
    res["type.id"] = type_id
    res["type.name"] = types[type_id]
    return res


def find_reservations_all(extids):
    """Get all reservations for a given set of objects."""
    n = client.service.findReservations(
        login={
            "username": username,
            "password": password,
            "applicationkey": key,
        },
        searchobjects={"object": [{"extid": id} for id in extids]},
        numberofreservations=1,
    ).totalnumberofreservations

    num_pages = -(-n // 1000)

    res = []
    for i in range(num_pages):
        page = client.service.findReservations(
            login={
                "username": username,
                "password": password,
                "applicationkey": key,
            },
            searchobjects={"object": [{"extid": id} for id in extids]},
            # TODO: Returntypes should be configurable. Some base values should
            # be used for title and location, configurable values should be
            # concatenated to form event description. Configure this from web
            # interface for connections.
            # TODO: Use English (e.g. `courseevt.coursename_eng`) for some
            # users? Or configurable for entire course instance.
            returntypes={
                "typefield": [
                    {
                        "type": "person_staff",
                        "field": ["person.id", "person.fullname"],
                    },
                    {
                        "type": "courseevt",
                        "field": [
                            "courseevt.uniqueid",
                            "courseevt.coursename",
                            "courseevt.coursename_eng",
                        ],
                    },
                    {"type": "activity", "field": ["activity.id"]},
                    {"type": "room", "field": ["room.name"]},
                ]
            },
            numberofreservations=1000,
            beginindex=i * 1000,
        )["reservations"]["reservation"]
        res += page
    return list(map(unpack_reservation, res))


def unpack_reservation(r):
    date_format = "%Y%m%dT%H%M%S"
    res = {
        "id": r["id"],
        "start_at": datetime.strptime(r["begin"], date_format),
        "end_at": datetime.strptime(r["end"], date_format),
        "length": r["length"],
        "modified": r["modified"],
    }
    for o in r["objects"]["object"]:
        type, fields = unpack_fields(o)
        res[type] = fields
    return res


def unpack_fields(object: dict) -> tuple[str, dict[str, str]]:
    """Takes a TimeEdit `object`. Return the object `type` and all its fields packed in a dict."""
    res = {}
    res["id"] = object["extid"]
    for f in object["fields"]["field"]:
        # NOTE: Assumption that there is only one value per field
        res[f["extid"]] = f["value"][0]
    return object["type"], res
