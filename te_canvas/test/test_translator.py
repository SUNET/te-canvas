import datetime
import unittest

import te_canvas.translator as translator
from te_canvas.timeedit import TimeEdit


class TestTranslator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    def test_translator(self):
        timeedit = TimeEdit()
        template = r"Hello ${person::firstname} how are you this ${date::weekday} in ${date::month}?"
        fields = [("person", "firstname"), ("date", "weekday"), ("date", "month")]
        objects = [
            {
                "extid": "john",
                "type": "person",
                "fields": {"firstname": "john", "lastname": "lennon"},
            },
            {
                "extid": "paul",
                "type": "person",
                "fields": {"firstname": "paul", "lastname": "mccartney"},
            },
            {
                "extid": "2022-03-24",
                "type": "date",
                "fields": {"iso": "2022-03-24", "weekday": "thursday", "month": "march"},
            },
        ]
        field_values = {"person::firstname": "john, paul", "date::weekday": "thursday", "date::month": "march"}
        string = "Hello john, paul how are you this thursday in march?"
        return_types = {"person": ["firstname"], "date": ["weekday", "month"]}
        canvas_event = {
            "title": "john, paul" + translator.TAG_TITLE,
            "location_name": "march",
            "description": "thursday"
            + f'<br><br><a href="{timeedit.reservation_url("example_id")}">Edit on TimeEdit</a>',
            "start_at": datetime.date(2022, 3, 25),
            "end_at": datetime.date(2022, 3, 25),
        }

        t = translator.Translator(
            None,
            timeedit,
            r"${person::firstname}",
            r"${date::month}",
            r"${date::weekday}",
        )

        self.assertEqual(translator._extract_fields(template), fields)
        self.assertEqual(translator._encode_fields(fields, objects), field_values)
        self.assertEqual(translator._return_types(fields), return_types)
        self.assertEqual(translator._string(template, fields, objects), string)

        self.assertEqual(
            t.canvas_event(
                {
                    "id": "example_id",
                    "objects": objects,
                    "start_at": datetime.date(2022, 3, 25),
                    "end_at": datetime.date(2022, 3, 25),
                }
            ),
            canvas_event,
        )

        # With ("random", "identifier") not in `fields`, a KeyError is raised.
        with self.assertRaises(KeyError):
            translator._string(r"some ${random::identifier}", fields, objects)

        # With ("random", "identifier") in `fields`, but no matching data in `objects`, the braced
        # identifier is replaced with the empty string.
        self.assertEqual(
            translator._string(r"some ${random::identifier}", fields + [("random", "identifier")], objects), "some "
        )
