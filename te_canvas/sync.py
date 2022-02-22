import te_canvas.canvas as canvas
import te_canvas.log as log
import te_canvas.te as te
from te_canvas.app import app
from te_canvas.db import Connection, Event, flat_list

logger = log.get_logger()


# Invariant 1: Events in database is a superset of (our) events on Canvas.
# Invariant 2: For every event e in the database, there exists a connection c s.t.
#              c.canvas_group = e.canvas_group and
#              c.te_group = e.te_group.
def sync_job():
    logger.info("Sync job started")
    canvas_groups_n = 0
    with app.db.sqla_session() as session:  # Any exception -> session.rollback()
        # Note the comma!
        for (canvas_group,) in session.query(Connection.canvas_group).distinct():
            canvas_groups_n += 1

            # Remove all events previously added by us to this Canvas group
            for event in session.query(Event).filter(
                Event.canvas_group == canvas_group
            ):
                # If this event does not exist on Canvas, this is a NOOP and no
                # exception is raised.
                canvas.delete_event(event.canvas_id)

            # Clear deleted events
            session.query(Event).filter(Event.canvas_group == canvas_group).delete()

            # Delete flagged connections
            session.query(Connection).filter(
                Connection.canvas_group == canvas_group, Connection.delete_flag == True
            ).delete()

            # Push to Canvas and add to database
            te_groups = flat_list(
                session.query(Connection.te_group).filter(
                    Connection.canvas_group == canvas_group
                )
            )

            logger.info(f"Processing: {te_groups} → {canvas_group}")
            for r in te.find_reservations_all(te_groups):
                # Try/finally ensures invariant 1.
                try:
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
                finally:
                    session.add(
                        Event(
                            te_id=r["id"],
                            canvas_id=canvas_event.id,
                            canvas_group=canvas_group,
                        )
                    )
    logger.info(f"Sync job completed; {canvas_groups_n} Canvas groups processed")
