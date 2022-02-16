import os
import sys
import unittest
import logging
import typing

from te_canvas.app import App
from te_canvas.db import DB, Connection, Event, Test


class TestAPI(unittest.TestCase):
    db = DB(
        hostname="localhost",
        port="5433",
        username="test_user",
        password="test_password",
        database="test_db",
    )
    with db.sqla_session() as session:
        session.query(Connection).delete()
        session.query(Event).delete()
        session.query(Test).delete()

    app = App(db)
    app.logger.setLevel(logging.CRITICAL)

    client = app.flask.test_client()

    def test_api_setup(self):
        """We're using the correct DB."""
        self.assertEqual(
            self.app.db.conn_str,
            "postgresql+psycopg2://test_user:test_password@localhost:5433/test_db",
        )

    def test_api_version(self):
        response = self.client.get("/api/version")
        self.assertEqual(response.status_code, 200)  # Success
        self.assertEqual(response.json, "v0.0.1")

    ############################################################################
    # /API/TIMEEDIT
    #
    # TODO: Some assertions are dependent on TE data, this seems unavoidable.
    # But perhaps we can make the data more well defined so that it can be
    # easily recreated on a new instance.
    ############################################################################

    unittest_room = {
        "extid": "fullroom_unittest",
        "general.id": "unittest",
        "general.title": "Unit Test Room",
        "room.id": "unittest",
        "room.name": "Unit Test Room",
        "type.id": "fullroom",
        "type.name": "Lokal (Hel)",
    }

    def test_api_te_types(self):
        response = self.client.get("/api/timeedit/types")
        self.assertEqual(response.status_code, 200)
        json = typing.cast(dict, response.json)
        self.assertTrue("room" in json)

    def test_api_te_object(self):
        response = self.client.get(
            "/api/timeedit/object", query_string={"extid": "fullroom_foobar"}
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.get(
            "/api/timeedit/object", query_string={"extid": "fullroom_unittest"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, self.unittest_room)

    def test_api_te_objects(self):
        response = self.client.get("/api/timeedit/objects")
        self.assertEqual(response.status_code, 400)  # Bad request
        self.assertEqual(
            response.json,
            {
                "errors": {
                    "type": "Missing required parameter in the JSON body or the post body or the query string"
                },
                "message": "Input payload validation failed",
            },
        )

        response = self.client.get(
            "/api/timeedit/objects", query_string={"type": "fullroom"}
        )
        self.assertEqual(response.status_code, 200)
        json = typing.cast(dict, response.json)
        self.assertTrue(
            {x: self.unittest_room[x] for x in ["extid", "general.id", "general.title"]}
            in json
        )

    def test_api_te_objects_searchstring(self):
        for x in ["", "unitt", "unittest"]:
            response = self.client.get(
                "/api/timeedit/objects",
                query_string={"type": "fullroom", "search_string": x},
            )
            json = typing.cast(dict, response.json)
            self.assertTrue(
                {
                    x: self.unittest_room[x]
                    for x in ["extid", "general.id", "general.title"]
                }
                in json
            )
            if x == "unittest":
                self.assertEqual(len(json), 1)

        response = self.client.get(
            "/api/timeedit/objects",
            query_string={"type": "fullroom", "search_string": "foobar"},
        )
        self.assertEqual(response.json, [])

    def test_api_te_objects_pagination(self):
        response = self.client.get(
            "/api/timeedit/objects", query_string={"type": "fullroom"}
        )
        self.assertEqual(response.status_code, 200)
        json = typing.cast(dict, response.json)
        fullrooms_all = json

        response = self.client.get(
            "/api/timeedit/objects",
            query_string={"type": "fullroom", "number_of_objects": 10},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, fullrooms_all[:10])

        response = self.client.get(
            "/api/timeedit/objects",
            query_string={
                "type": "fullroom",
                "number_of_objects": 10,
                "begin_index": 5,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, fullrooms_all[5:15])

    ############################################################################
    # /API/CANVAS
    #
    ############################################################################

    def test_api_canvas(self):
        response = self.client.get("/api/canvas/courses")
        self.assertEqual(response.status_code, 200)
        json = typing.cast(dict, response.json)
        self.assertGreater(len(json), 0)

    ############################################################################
    # /API/CONNECTION
    #
    ############################################################################

    def test_api_connection(self):
        response = self.client.get("/api/connection")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, [])

        response = self.client.post(
            "/api/connection", data={"te_group": "foo", "canvas_group": "bar"}
        )
        self.assertEqual(response.status_code, 204)  # No content

        response = self.client.post(
            "/api/connection", data={"te_group": "foo", "canvas_group": "bar"}
        )
        self.assertEqual(response.status_code, 409)  # Conflict

        response = self.client.get("/api/connection")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json,
            [{"te_group": "foo", "canvas_group": "bar", "delete_flag": False}],
        )

        response = self.client.delete(
            "/api/connection", data={"te_group": "foo", "canvas_group": "bar"}
        )
        self.assertEqual(response.status_code, 204)

        response = self.client.delete(
            "/api/connection", data={"te_group": "foo", "canvas_group": "bar"}
        )
        # self.assertEqual(response.status_code, 409) # TODO: This should not be quite 400 nor 204 – The delete flag is set but it has not been deleted yet (by the sync job)


if __name__ == "__main__":
    unittest.main()