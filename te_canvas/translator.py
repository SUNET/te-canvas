"""
This module gathers functionality for "translating" a TimeEdit event into a Canvas event and dealing
with templates related to this.
"""

from te_canvas.db import DB
from te_canvas.util import TemplateConfigState

# Used to differentiate te-canvas events from manually added Canvas events, this string is added as
# a suffix to each event title. These are zero-width spaces, an invisible unicode character. We use
# 10 because why not, it should reduce the risk of false positive.
TAG_TITLE = r"​​​​​​​​​​"


class TemplateError(Exception):
    pass


class Translator:
    """
    Translator creates Canvas events from TimeEdit events based on a set of template strings.

    Template strings are read from the database only at Translator initialization. So for any given
    Translator instance t, t.canvas_event is a pure function.
    """

    def __init__(self, db: DB, timeedit):
        """
        Read template strings from the database and extract fields (used for template functionality)
        and return types (used as arguments in TimeEdit API calls).

        Raises:
            TemplateError, if any of the required template strings (title, location, description) is
            missing or empty.
        """
        self.db = db
        self.timeedit = timeedit
        template = self.__get_template_config()
        self.template_title = self.__extract_template(template, "title")
        self.template_location = self.__extract_template(template, "location")
        self.template_description = self.__extract_template(template, "description")
        self.return_types = self.__extract_return_types(template)

    def __extract_template(self, template, name: str) -> "list[dict[str, str]]":
        """
        Extract template from db query.

        Used for translating timeedit reservations.
        """
        return [{t: f} for (_, n, t, f, _) in template if n == name]

    def __extract_return_types(self, template) -> "dict[str, list[str]]":
        """
        Extract return types from db query.

        Used in API call to timeedit when getting reservations.
        """
        te_types = set(t for (_, _, t, _, _) in template)
        return {te_type: [f for (_, _, t, f, _) in template if t == te_type] for te_type in te_types}

    def canvas_event(self, timeedit_reservation: dict) -> "dict[str,str]":
        """
        Create canvas event from timeedit reservations.
        """
        return {
            "title":         self.__translate_fields(self.template_title, timeedit_reservation["objects"]) + TAG_TITLE,
            "location_name": self.__translate_fields(self.template_location, timeedit_reservation["objects"]),
            "description":   self.__translate_fields(self.template_description, timeedit_reservation["objects"])
                + f'<br><br><a href="{self.timeedit.reservation_url(timeedit_reservation["id"])}">Edit on TimeEdit</a>',
            "start_at": timeedit_reservation["start_at"],
            "end_at":   timeedit_reservation["end_at"],
            }  # fmt: skip

    def state(self) -> TemplateConfigState:
        """
        Return an object allowing instances of Translator to be compared.

        Used for change detection in sync.py.
        """
        return {
            "title": self.template_title,
            "location": self.template_location,
            "description": self.template_description,
        }

    def __get_template_config(self):
        """
        Get a template config.

        We need atleast one field for each name.
        Else we raise TemplateError.
        """
        res = self.db.get_template_config()
        name_count = set(name for (_, name, _, _, _) in res)
        if len(name_count) < 3:
            raise TemplateError
        return res

    def __translate_fields(self, template: "list[dict[str,str]]", objects: "list[dict]") -> str:
        """
        Used for translating fields from te reservations according to template.
        """
        selected_fields = []
        for o in objects:
            te_type = o["type"]
            for te_field, content in o["fields"].items():
                if {te_type: te_field} in template:
                    selected_fields.append(content)
        return " ".join(selected_fields)
