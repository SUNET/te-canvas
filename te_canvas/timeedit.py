import os
import sys
import itertools
from datetime import datetime
from typing import Optional, Any

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
        result = f"https://cloud.timeedit.net/{self.ID}/web/{self.USERGROUP}/ri.html?id={id}&{static_args}"
        logger.info("******************* [TimeEdit.reservation_url] *******************")
        logger.info(f"{result}")
        logger.info("==================================================================")
        return result

    def find_types_all(self):
        res = self.client.service.findTypes(
            login=self.login,
            ignorealias=False,
        )
        if len(res) == 0:
            logger.warning("te.find_types_all() returned 0 types.")
        logger.info("******************* [TimeEdit.find_types_all] *******************")
        logger.info(f"{res}")
        logger.info("==================================================================")
        return {t["extid"]: t["name"] for t in res + [{"extid": "reservation", "name": "Reservation"}]}

    def get_type(self, extid: str):
        if extid == "reservation":
            return {"name": "Reservation"}
        res = self.client.service.getTypes(login=self.login, ignorealias=False, types=[extid])
        logger.info("******************* [TimeEdit.get_type] *******************")
        logger.info(f"{res}")
        logger.info("==================================================================")
        return res[0] if len(res) > 0 else {"extid": extid, "name": ""}

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
        logger.info("******************* [TimeEdit.find_objects] *******************")
        logger.info(f"{resp}")
        logger.info("==================================================================")
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
        logger.info("******************* [TimeEdit.find_objects_all] *******************")
        logger.info(f"{res}")
        logger.info("==================================================================")
        return res

    def find_object_fields(self, extid: "str") -> list:
        """Get fields specification of type"""
        res = self.client.service.findObjectFields(login=self.login, types=[extid])
        logger.info("******************* [TimeEdit.find_object_fields] *******************")
        logger.info(f"{res}")
        logger.info("==================================================================")
        return list(res)

    def get_field_defs(self, extid: str) -> dict:
        res = self.client.service.getFieldDefs(login=self.login, fields=[extid])
        defs = [
            {"extid": r["extid"], "name": r["name"]}
            for r in res
            if r["extid"] not in self.SEARCH_FIELDS + self.RETURN_FIELDS
        ]
        logger.info("******************* [TimeEdit.get_field_defs] *******************")
        logger.info(f"{defs}")
        logger.info("==================================================================")
        return defs[0] if len(defs) > 0 else {}

    def get_object(self, extid: str) -> Optional[dict]:
        """Get a specific object based on external id."""
        resp = self.client.service.getObjects(
            login=self.login,
            objects={"object": [extid]},
        )
        if resp is None:
            return None
        logger.info("******************* [TimeEdit.get_object] *******************")
        logger.info(f"{resp}")
        logger.info("==================================================================")
        return list(map(_unpack_object, resp))[0]

    def find_reservation_fields(self):
        field_defs = self.client.service.findReservationFields(login=self.login)

        resp =  list(filter(lambda field_def: field_def.split(".")[0] == "res", field_defs))
        logger.info("******************* [TimeEdit.find_reservation_fields] *******************")
        logger.info(f"{resp}")
        logger.info("==================================================================")
        return resp

    def find_reservations_all(self, extids: "list[str]", return_types: "dict[str, list[str]]"):
        """Get all reservations for a given set of objects."""
        # If extids is empty, findReservations will return *all* reservations, which is never what
        # we want
        if len(extids) == 0:
            return []

        res_return_fields = []
        if "reservation" in return_types:
            res_return_fields = return_types["reservation"]
            return_types.pop("reservation")

        return_types_packed = {
            "typefield": [
                {
                    "type": te_type,
                    "field": te_fields,
                }
                for te_type, te_fields in return_types.items()
            ]
        }
        logger.info("******************* [TimeEdit.find_reservations_all.params] *******************")
        logger.info(f"{extids}")
        logger.info(f"{return_types}")
        logger.info("res_return_fields")
        logger.info(f"{res_return_fields}")
        logger.info("return_types_packed")
        logger.info(f"{return_types_packed}")
        logger.info("==================================================================")
        
        n = self.client.service.findReservations(
            login=self.login,
            searchobjects={"object": [{"extid": id} for id in extids]},
            numberofreservations=1,
        ).totalnumberofreservations

        num_pages = -(-n // 1000)

        reservations = []
        
        try:
            pages = [
                self.client.service.findReservations(
                    login=self.login,
                    searchobjects={"object": [{"extid": ext_id} for ext_id in extids]},
                    numberofreservations=1000,
                    beginindex=i * 1000,
                    returntypes=return_types_packed,
                    returnfields= {"field": res_return_fields},
                )["reservations"]["reservation"]
                for i in range(num_pages)
            ]
            
            reservations = list(itertools.chain.from_iterable(pages))

        except Exception as e:
            logger.error("Error in find_reservations_all(%s): %s", extids, e, stack_info=True)
            return []
        
        if not reservations:
            logger.warning("find_reservations_all(%s) returned 0 reservations.", extids)
        
        unpacked_reservations = []
        for r in reservations:
            unpacked_reservations.append(_unpack_reservation(r, res_return_fields))
        logger.info("******************* [TimeEdit.find_reservations_all] *******************")
        logger.info(f"{unpacked_reservations}")
        logger.info("==================================================================")
        return unpacked_reservations


# ---- Helper functions --------------------------------------------------------


def _unpack_object(o):
    res = {"extid": o["extid"]}
    for f in o["fields"]["field"]:
        res[f["extid"]] = f["value"][0]
    return res


def _parse_datetime(date_str: str, date_format: str = "%Y%m%dT%H%M%S") -> datetime | None:
    """Parses a datetime string safely, returning None if parsing fails."""
    try:
        return datetime.strptime(date_str, date_format)
    except (ValueError, TypeError):
        return None

def _unpack_reservation_object(obj: dict[str, Any]) -> dict[str, Any]:
    """Extracts a structured representation of a reservation object."""
    return {
        "type": obj.get("type", ""),
        "extid": obj.get("extid", ""),
        "fields": {f["extid"]: f["value"][0] for f in obj.get("fields", {}).get("field", []) if "value" in f}
    }
    
def _unpack_reservation(reservation, res_return_fields):
            
    # Extract reservation objects safely
    objects = [_unpack_reservation_object(o) for o in reservation.get("objects", {}).get("object", [])]
    
    unpacked_res = {
        "id": reservation.get("id"),
        "start_at": _parse_datetime(reservation.get("begin")),
        "end_at": _parse_datetime(reservation.get("end")),
        "length": reservation.get("length"),
        "modified": _parse_datetime(reservation.get("modified")),
        "objects": objects,
    }

    # We may need to add fields from the reservation object.
    res_return_fields = set(res_return_fields) 
    # Ensure 'fields' and 'field' exist and are iterable
    fields = reservation.get("fields", {}).get("field", [])
    if fields:
        field_mapping = {field["extid"]: field["value"][0] for field in fields if "value" in field}
        unpacked_res.update({res_field: field_mapping[res_field] for res_field in res_return_fields if res_field in field_mapping})

    return unpacked_res
