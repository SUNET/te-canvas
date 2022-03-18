import os
import sys
from datetime import datetime
from typing import Optional

import zeep

from te_canvas.log import get_logger

logger = get_logger()


class TimeEdit:
    def __init__(self):
        try:
            wsdl = os.environ["TE_WSDL_URL"]
            cert = os.environ["TE_CERT"]
            username = os.environ["TE_USERNAME"]
            password = os.environ["TE_PASSWORD"]
        except Exception as e:
            logger.critical(f"Failed to load configuration: {e}, exiting.")
            sys.exit(-1)

        try:
            self.client = zeep.Client(wsdl)
            key = self.client.service.register(cert).applicationkey
        except Exception:
            logger.critical(f'TimeEdit connection to "{wsdl}" failed, exiting.')
            sys.exit(-1)

        self.login = {
            "username": username,
            "password": password,
            "applicationkey": key,
        }

    def find_types_all(self):
        res = self.client.service.findTypes(
            login=self.login,
            ignorealias=False,
        )
        if len(res) == 0:
            logger.warning("te.find_types_all() returned 0 types.")
        return {t["extid"]: t["name"] for t in res}

    # TODO: Add returnFields parameter, populate from getAlFields?
    def find_objects(self, type, number_of_objects, begin_index, search_string):
        """Get max 1000 objects of a given type."""
        resp = self.client.service.findObjects(
            login=self.login,
            type=type,
            numberofobjects=number_of_objects,
            beginindex=begin_index,
            generalsearchfields={"field": ["general.id", "general.title"]},
            generalsearchstring=search_string,
            returnfields=["general.id", "general.title"],
        )
        if resp.objects is None:
            # Can't really warn about this generally since this endpoint is used for searching.
            # logger.warning("te.find_objects(${type}, ${number_of_objects}, ${begin_index}, ${search_string}) returned 0 objects.")
            return []
        return list(map(self.__unpack_object, resp["objects"]["object"]))

    def find_objects_all(self, type, search_string):
        """Get all objects of a given type."""
        n = self.client.service.findObjects(
            login=self.login,
            type=type,
            numberofobjects=1,
            generalsearchfields={"field": ["general.id", "general.title"]},
            generalsearchstring=search_string,
        ).totalnumberofobjects

        num_pages = -(-n // 1000)

        res = []
        for i in range(num_pages):
            page = self.find_objects(type, 1000, i * 1000, search_string)
            res += page
        return res

    def __unpack_object(self, o):
        res = {"extid": o["extid"]}
        for f in o["fields"]["field"]:
            res[f["extid"]] = f["value"][0]
        return res

    def get_object(self, extid: str) -> Optional[dict]:
        """Get a specific object based on external id."""
        resp = self.client.service.getObjects(
            login=self.login,
            objects={"object": [extid]},
        )
        if resp is None:
            return None
        res = list(map(self.__unpack_object, resp))[0]
        types = self.find_types_all()
        # NOTE: Assumption that external id is of form <type>_id
        type_id = res["extid"].split("_")[0]
        res["type.id"] = type_id
        res["type.name"] = types[type_id]
        return res

    def find_reservations_all(self, extids):
        """Get all reservations for a given set of objects."""

        # If extids is empty, findReservations will return *all* reservations, which
        # is never what we want
        if len(extids) == 0:
            return []

        n = self.client.service.findReservations(
            login=self.login,
            searchobjects={"object": [{"extid": id} for id in extids]},
            numberofreservations=1,
        ).totalnumberofreservations

        num_pages = -(-n // 1000)

        res = []
        for i in range(num_pages):
            page = self.client.service.findReservations(
                login=self.login,
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
        if len(res) == 0:
            logger.warning(
                f"te.find_reservations_all({extids}) returned 0 reservations."
            )
        return list(map(self.__unpack_reservation, res))

    def __unpack_reservation(self, r):
        date_format = "%Y%m%dT%H%M%S"
        res = {
            "id": r["id"],
            "start_at": datetime.strptime(r["begin"], date_format),
            "end_at": datetime.strptime(r["end"], date_format),
            "length": r["length"],
            "modified": r["modified"],
            "objects": {},
        }
        for o in r["objects"]["object"]:
            type, fields = self.__unpack_fields(o)
            res["objects"][type] = fields
        return res

    def __unpack_fields(self, object: dict) -> tuple[str, dict[str, str]]:
        """Takes a TimeEdit `object`. Return the object `type` and all its fields packed in a dict."""
        res = {}
        res["extid"] = object["extid"]
        for f in object["fields"]["field"]:
            # NOTE: Assumption that there is only one value per field
            res[f["extid"]] = f["value"][0]
        return object["type"], res
