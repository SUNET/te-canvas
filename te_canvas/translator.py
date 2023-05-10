"""
This module gathers functionality for "translating" a TimeEdit event into a Canvas event and dealing
with templates related to this.
"""

from te_canvas.db import DB
from te_canvas.types.config_type import ConfigType
from te_canvas.types.sync_state import SyncState
from te_canvas.types.template_config import TemplateConfig
from te_canvas.types.template_return_types import TemplateReturnTypes

# Used to differentiate te-canvas events from manually added Canvas events, this string is added as
# a suffix to each event title. These are zero-width spaces, an invisible unicode character. We use
# 10 because why not, it should reduce the risk of false positive.
TAG_TITLE = r"​​​​​​​​​​"

# Separators used when joining fields in Translator.__translate_fields()
LOCATION_SEPARATOR = " - "
TITLE_SEPARATOR = " - "
DESCRIPTION_SEPARATOR = "<br>"


class TemplateError(Exception):
    pass


class Translator:
    """
    Translator creates Canvas events from TimeEdit events based on a set of template strings.

    Template configuration are read from the database only at Translator initialization. So for any given
    Translator instance t, t.canvas_event is a pure function.
    """

    def __init__(self, db: DB, timeedit):
        """
        Read template configuration from the database and extract fields (used for template functionality)
        and return types (used as arguments in TimeEdit API calls).

        Raises:
            TemplateError, if no valid group or default template config.
        """
        self.db = db
        self.timeedit = timeedit
        template_data = self.__get_template_config()
        self.templates = self.__create_templates(template_data)
        self.return_types = self.__create_return_types(self.templates)

    def __create_templates(self, template) -> dict[str, TemplateConfig]:
        """
        Create templates from db query.

        Used for translating timeedit reservations.
        """
        groups_with_config = set(cg for (_, _, _, _, cg) in template)
        # All groups with atleast one config entry.
        groups = {
            cg: {
                ConfigType.TITLE.value: [],
                ConfigType.LOCATION.value: [],
                ConfigType.DESCRIPTION.value: [],
            }
            for cg in groups_with_config
        }
        for _, ct, t, f, cg in template:
            groups[cg][ct].append({t: f})
        # Filter out groups without valid config.
        return {
            key: groups[key] for key in groups.keys() if self.__is_valid(groups[key])
        }

    def __is_valid(self, template: TemplateConfig) -> bool:
        """
        Valid template config must have atleast one entry of each config_type.
        """
        config_types = set(ct for ct, entries in template.items() if len(entries) > 0)
        return len(config_types) == 3

    def __create_return_types(
        self,
        templates: dict[str, TemplateConfig],
    ) -> dict[str, TemplateReturnTypes]:
        """
        Create return types.

        Used in API call to timeedit when getting reservations.
        """
        return_types = {}
        for key in templates.keys():
            return_types[key] = self.__extract_fields(templates[key])
        return return_types

    def __extract_fields(self, template: TemplateConfig) -> TemplateReturnTypes:
        """
        Extract unique te_type:te_field combinations.
        Disregard config_type since it's not a timeedit concept.
        """
        te_types = set(
            te_type
            for ct in template.values()
            for entry in ct
            for te_type, _ in entry.items()
        )
        return_types = {
            te_type: [
                f
                for entries in template.values()
                for e in entries
                for t, f in e.items()
                if t == te_type
            ]
            for te_type in te_types
        }
        return {
            te_type: list(dict.fromkeys(te_fields))
            for te_type, te_fields in return_types.items()
        }

    def get_return_types(self, canvas_group: str) -> TemplateReturnTypes:
        if canvas_group in self.return_types:
            return self.return_types[canvas_group]
        if "default" in self.return_types:
            return self.return_types["default"]
        raise TemplateError

    def canvas_event(
        self, timeedit_reservation: dict, canvas_group: str
    ) -> "dict[str,str]":
        """
        Create canvas event from timeedit reservations.
        """
        return {
            "title":         self.__translate_fields(canvas_group, ConfigType.TITLE.value,timeedit_reservation["objects"], TITLE_SEPARATOR) + TAG_TITLE,
            "location_name": self.__translate_fields(canvas_group, ConfigType.LOCATION.value, timeedit_reservation["objects"], LOCATION_SEPARATOR),
            "description":   self.__translate_fields(canvas_group, ConfigType.DESCRIPTION.value, timeedit_reservation["objects"], DESCRIPTION_SEPARATOR)
                + f'<br><br><a href="{self.timeedit.reservation_url(timeedit_reservation["id"])}">Edit on TimeEdit</a>',
            "start_at": timeedit_reservation["start_at"],
            "end_at":   timeedit_reservation["end_at"],
            }  # fmt: skip

    def get_state(self, canvas_group: str) -> SyncState:
        """
        Return an object allowing instances of Translator to be compared.

        Used for change detection in sync.py.
        """
        state = {}
        if "default" in self.templates:
            state["default"] = "".join(
                [
                    "".join([ct, t, f])
                    for ct in self.templates["default"].keys()
                    for entry in self.templates["default"][ct]
                    for t, f in entry.items()
                ]
            )

        if canvas_group in self.templates:
            state[canvas_group] = "".join(
                [
                    "".join([ct, t, f])
                    for ct in self.templates[canvas_group].keys()
                    for entry in self.templates[canvas_group][ct]
                    for t, f in entry.items()
                ]
            )
        return state

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

    def __translate_fields(
        self, canvas_group: str, config_type: str, objects: "list[dict]", separator: str
    ) -> str:
        """
        Used for translating fields from te reservations according to template.
        """
        template_config = (
            self.templates[canvas_group]
            if canvas_group in self.templates.keys()
            else self.templates["default"]
        )
        selected_fields = []
        for o in objects:
            te_type = o["type"]
            for te_field, content in o["fields"].items():
                if {te_type: te_field} in template_config[config_type]:
                    selected_fields.append(content)
        return separator.join(selected_fields)
