"""
This module gathers functionality for "translating" a TimeEdit event into a Canvas event and dealing
with templates related to this.
"""

import re
from string import Template

from sqlalchemy.exc import NoResultFound  # type: ignore

from te_canvas.util import State

# Used to differentiate te-canvas events from manually added Canvas events. These are zero-width
# spaces, an invisible unicode character. We use 10 because why not, it should reduce the risk of
# false positive.
TAG_TITLE = r"​​​​​​​​​​"


class TemplateError(Exception):
    pass


class Translator:
    """
    Translator creates Canvas events from TimeEdit events based on a set of template strings.

    Template strings are read from the database only at Translator initialization. So for any given
    Translator instance t, t.canvas_event is a pure function.
    """

    def __init__(
        self,
        db,
        timeedit,
        title=None,
        location=None,
        description=None,
    ):
        """
        Read template strings from the database and extract fields (used for template functionality)
        and return types (used as arguments in TimeEdit API calls).

        Raises:
            TemplateError, if any of the required template strings (title, location, description) is
            missing or empty.
        """
        self.db = db
        self.timeedit = timeedit
        self.template_title = title or self.template("title")
        self.template_location = location or self.template("location")
        self.template_description = description or self.template("description")

        self.fields = (
            _extract_fields(self.template_title)
            + _extract_fields(self.template_location)
            + _extract_fields(self.template_description)
        )

        self.return_types = _return_types(self.fields)

    def canvas_event(self, timeedit_reservation):
        return {
            "title":         _string(self.template_title,       self.fields, timeedit_reservation["objects"]) + TAG_TITLE,
            "location_name": _string(self.template_location,    self.fields, timeedit_reservation["objects"]),
            "description":   _string(self.template_description, self.fields, timeedit_reservation["objects"])
                + f'<br><br><a href="{self.timeedit.reservation_url(timeedit_reservation["id"])}">Edit on TimeEdit</a>',
            "start_at": timeedit_reservation["start_at"],
            "end_at":   timeedit_reservation["end_at"],
            }  # fmt: skip

    def state(self) -> State:
        """
        Return an object allowing instances of Translator to be compared.

        Used for change detection in sync.py.
        """
        return {
            "title": self.template_title,
            "location": self.template_location,
            "description": self.template_description,
        }

    def template_config_ok(self) -> bool:
        """
        Check if we have a complete event template definition.
        """
        try:
            for k in ["title", "location", "description"]:
                self.template(k)
        except TemplateError:
            return False
        return True

    def template(self, key: str) -> str:
        """
        Get a template string, raise TemplateError if missing or empty.
        """
        try:
            res = self.db.get_config(key)
        except NoResultFound:
            raise TemplateError
        if res == "":
            raise TemplateError
        return res


# ---- Helper functions --------------------------------------------------------

SEPARATOR = "::"


class MyTemplate(Template):
    """
    We use a custom subclass of Template to allow any characters in braced identifiers.

    We consider only braced identifiers.
    """

    braceidpattern = r"[^}]*"


def _string(template, fields, objects):
    """
    Produce a string with variables substituted.

    Variables of the form ${foo::bar} are substituted for the field bar on object foo.
    """
    s = MyTemplate(template)
    return s.substitute(_encode_fields(fields, objects))


def _encode_fields(tuples, objects):
    return {
        SEPARATOR.join([type, field]): ", ".join([o["fields"][field] for o in objects if o["type"] == type])
        for (type, field) in tuples
    }


def _extract_fields(template: str) -> list[tuple[str, str]]:
    """
    Extract (type, field)-tuples from a template string.
    """
    return [tuple(pat.split(SEPARATOR)) for pat in re.findall(r"(?<=\${).*?(?=})", template)]


def _return_types(tuples):
    """
    Extract return types from a list of (type, field)-tuples.
    Returns:
        A dict { T: F[] }, meaning that for objects of type T we want to get fields F.
    """
    types = set([type for (type, _) in tuples])
    return {type: [field for (type_, field) in tuples if type_ == type] for type in types}
