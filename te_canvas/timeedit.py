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
            cert = os.environ["TE_CERT"]
            username = os.environ["TE_USERNAME"]
            password = os.environ["TE_PASSWORD"]
            self.ID = os.environ["TE_ID"]
            self.USERGROUP = os.environ["TE_USERGROUP"]

            # These fields must exist.
            # What fields exist varies across TE instances.
            self.SEARCH_FIELDS = os.environ["TE_SEARCH_FIELDS"].split(",")
            # If found, must be mandatory for sorting.
            # Mandatory fields varies across TE instances.
            self.RETURN_FIELDS = os.environ["TE_RETURN_FIELDS"].split(",")
        except Exception as e:
            logger.critical(f"Missing env var: {e}")
            sys.exit(1)

        wsdl = f"https://cloud.timeedit.net/soap/3/{self.ID}/wsdl"

        try:
            self.client = zeep.Client(wsdl)  # type: ignore
            key = self.client.service.register(cert).applicationkey
        except Exception:
            logger.critical(f'TimeEdit connection to "{wsdl}" failed, exiting.')
            sys.exit(1)

        self.login = {
            "username": username,
            "password": password,
            "applicationkey": key,
        }

    def reservation_url(self, id: str) -> str:
        # These query args are not understood in detail, taken blindly from the URL we get when
        # navigating to an event detail page in web view
        static_args = "h=t&sid=4&types=0&fe=0&fr=t&step=0&ef=2&nocache=2"
        return f"https://cloud.timeedit.net/{self.ID}/web/{self.USERGROUP}/ri.html?id={id}&{static_args}"

    def find_types_all(self):
        res = self.client.service.findTypes(
            login=self.login,
            ignorealias=False,
        )
        if len(res) == 0:
            logger.warning("te.find_types_all() returned 0 types.")
        return {t["extid"]: t["name"] for t in res}

    def find_objects(self, type, number_of_objects, begin_index, search_string):
        """Get max 1000 objects of a given type."""
        resp = self.client.service.findObjects(
            login=self.login,
            type=type,
            numberofobjects=number_of_objects,
            beginindex=begin_index,
            generalsearchfields={"field": self.SEARCH_FIELDS},
            generalsearchstring=search_string,
            returnfields=self.RETURN_FIELDS,
        )
        if resp.objects is None:
            # Can't really warn about this generally since this endpoint is used for searching.
            # logger.warning("te.find_objects(${type}, ${number_of_objects}, ${begin_index}, ${search_string}) returned 0 objects.")
            return []
        return list(map(_unpack_object, resp["objects"]["object"]))

    def find_objects_all(self, type, search_string):
        """Get all objects of a given type."""
        n = self.client.service.findObjects(
            login=self.login,
            type=type,
            numberofobjects=1,
            generalsearchfields={"field": self.SEARCH_FIELDS},
            generalsearchstring=search_string,
        ).totalnumberofobjects

        num_pages = -(-n // 1000)

        res = []
        for i in range(num_pages):
            page = self.find_objects(type, 1000, i * 1000, search_string)
            res += page
        return res

    def find_object_fields(self, extid: "str"):
        """Get fields specification of type"""
        res = self.client.service.findObjectFields(login=self.login, types=[extid])
        return list(res)

    def get_field_defs(self, extids):
        res = self.client.service.getFieldDefs(login=self.login, fields=extids)
        return [
            {r["extid"]: r["name"]}
            for r in res
            if r["extid"] not in self.SEARCH_FIELDS + self.RETURN_FIELDS
        ]

    def get_object(self, extid: str) -> Optional[dict]:
        """Get a specific object based on external id."""
        resp = self.client.service.getObjects(
            login=self.login,
            objects={"object": [extid]},
        )
        if resp is None:
            return None
        return list(map(_unpack_object, resp))[0]

    def find_reservations_all(
        self, extids: "list[str]", return_types: "dict[str, list[str]]"
    ):
        """Get all reservations for a given set of objects."""

        # If extids is empty, findReservations will return *all* reservations, which is never what
        # we want
        if len(extids) == 0:
            return []

        return_types_packed = {
            "typefield": [
                {
                    "type": type,
                    "field": fields,
                }
                for type, fields in return_types.items()
            ]
        }

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
                numberofreservations=1000,
                beginindex=i * 1000,
                returntypes=return_types_packed,
            )["reservations"]["reservation"]
            res += page
        if len(res) == 0:
            logger.warning(
                "te.find_reservations_all(%s) returned 0 reservations.", extids
            )

        return list(map(_unpack_reservation, res))


# ---- Helper functions --------------------------------------------------------


def _unpack_object(o):
    res = {"extid": o["extid"]}
    for f in o["fields"]["field"]:
        res[f["extid"]] = f["value"][0]
    return res


def _unpack_reservation(r):
    date_format = "%Y%m%dT%H%M%S"

    if r["objects"] is None:
        objects = []
    else:
        objects = [_unpack_reservation_object(o) for o in r["objects"]["object"]]

    return {
        "id": r["id"],
        "start_at": datetime.strptime(r["begin"], date_format),
        "end_at": datetime.strptime(r["end"], date_format),
        "length": r["length"],
        "modified": datetime.strptime(r["modified"], date_format),
        "objects": objects,
    }


def _unpack_reservation_object(object: dict) -> dict:
    return {
        "type": object["type"],
        "extid": object["extid"],
        "fields": {f["extid"]: f["value"][0] for f in object["fields"]["field"]},
    }
