import re
from string import Template

from sqlalchemy.exc import NoResultFound

from te_canvas.util import State

# This module gathers functionality for "translating" a TimeEdit event into a Canvas event and
# dealing with templates related to this.

# Used to identify synced events
TAG_TITLE = r"​"


class TemplateError(Exception):
    pass


# This class reads from the database only at initialization. So for any given Translator instance t,
# t.canvas_event is a pure function.
class Translator:
    # Raises TemplateError
    def __init__(
        self,
        db,
        timeedit,
        title=None,
        location=None,
        description=None,
    ):
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

    # Used for change detection in sync job
    def state(self) -> State:
        return {
            "title": self.template_title,
            "location": self.template_location,
            "description": self.template_description,
        }

    # Check if we have a complete event template definition
    def template_config_ok(self) -> bool:
        try:
            for k in ["title", "location", "description"]:
                self.template(k)
        except TemplateError:
            return False
        return True

    # Get template string, raise TemplateError if missing or empty
    def template(self, key: str) -> str:
        try:
            res = self.db.get_config(key)
        except NoResultFound:
            raise TemplateError
        if res == "":
            raise TemplateError
        return res


# ---- Helper functions --------------------------------------------------------

SEPARATOR = "::"

# Subclass to allow any characters in braced identifiers. We consider only braced identifiers.
class MyTemplate(Template):
    braceidpattern = r"[^}]*"


def _string(template, fields, objects):
    s = MyTemplate(template)
    return s.substitute(_encode_fields(fields, objects))


def _encode_fields(tuples, objects):
    return {
        SEPARATOR.join([type, field]): ", ".join([o["fields"][field] for o in objects if o["type"] == type])
        for (type, field) in tuples
    }


# Dict { T: F[] }, meaning that for objects of type T we want to get fields F
def _return_types(tuples):
    types = set([type for (type, _) in tuples])
    return {type: [field for (type_, field) in tuples if type_ == type] for type in types}


# Extract (type, field) tuples from a template string
def _extract_fields(template: str) -> list[tuple[str, str]]:
    return [tuple(pat.split(SEPARATOR)) for pat in re.findall(r"(?<=\${).*?(?=})", template)]
