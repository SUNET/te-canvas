import re
from string import Template

# This module gathers functionality for "translating" a TimeEdit event into a
# Canvas event and dealing with templates related to this.

EVENT_TAG = r'<br><em><span style="font-size: 8pt;">Event added by TimeEdit integration</span></em>'


class Translator:
    def __init__(self, title, location, description):
        self.template_title = title
        self.template_location = location
        self.template_description = description

        self.fields = (
            _extract_fields(self.template_title)
            + _extract_fields(self.template_location)
            + _extract_fields(self.template_description)
        )

        self.return_types = _return_types(self.fields)

    def canvas_event(self, timeedit_reservation):
        return {
            "title": _string(self.template_title, self.fields, timeedit_reservation["objects"]),
            "location_name": _string(self.template_location, self.fields, timeedit_reservation["objects"]),
            "description": _string(self.template_description, self.fields, timeedit_reservation["objects"]) + EVENT_TAG,
            "start_at": timeedit_reservation["start_at"],
            "end_at": timeedit_reservation["end_at"],
        }


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
