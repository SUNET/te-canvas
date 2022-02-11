import te_canvas.canvas as canvas
import te_canvas.log as log
import te_canvas.te as te
from te_canvas.db.session import sqla_session
from te_canvas.db.model import Connection, Event

logger = log.get_logger()


# TODO: Error handling
def sync_job():
    with sqla_session() as session:
        # Note the comma!
        for (canvas_group,) in session.query(Connection.canvas_group).distinct():
            print(f"Canvas group: {canvas_group}")

            # Remove all events previously added by us to this Canvas group
            for event in session.query(Event).filter(
                Event.canvas_group == canvas_group
            ):
                print(f"Event: {event.canvas_id}")
                # canvas.delete_event(canvas_id)

            # Clear deleted events
            session.query(Event).filter(Event.canvas_group == canvas_group).delete()

            # Delete flagged connections
            session.query(Connection).filter(
                Connection.canvas_group == canvas_group and Connection.delete_flag
            ).delete()

            # Push to Canvas and add to database
            te_groups = (
                session.query(Connection.te_group)
                .filter(Connection.canvas_group == canvas_group)
                .all()
            )
            for r in te.find_reservations_all(te_groups):
                # TODO: Use configured values to create description.
                canvas_event = canvas.create_event(
                    {
                        "context_code": f"course_{canvas_group}",
                        "title": r["activity"]["activity.id"],
                        "location_name": r["room"]["room.name"],
                        "description": "<br>".join(
                            [
                                r["courseevt"]["courseevt.coursename"],
                                r["person_staff"]["person.fullname"],
                            ]
                        ),
                        "start_at": r["start_at"],
                        "end_at": r["end_at"],
                    }
                )

                session.add(
                    Event(
                        te_id=r["id"],
                        canvas_id=canvas_event.id,
                        canvas_group=canvas_group,
                    )
                )
