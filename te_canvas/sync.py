import te_canvas.canvas as canvas
import te_canvas.log as log
import te_canvas.te as te
from te_canvas.db.session import sqla_session
from te_canvas.db.model import Connection, Event

logger = log.get_logger()


def sync_job():
    with sqla_session() as session:
        for c in session.query(Connection):
            logger.info(
                f'Syncing from TimeEdit: {c.te_group} to Canvas: {c.canvas_group}'
            )

            # Remove all events previously added by us
            for row in session.query(Event).filter(
                Event.te_group == c.te_group
                and Event.canvas_group == c.canvas_group
            ):
                if not canvas.delete_event(row.canvas_id):
                    break

            # Clear database
            session.query(Event).filter(
                Event.te_group == c.te_group
                and Event.canvas_group == c.canvas_group
            ).delete()

            # If the connection has been flagged for deletion
            if c.delete_flag:
                session.delete(c)
                continue

            # Push to Canvas and add to database
            for r in te.get_reservations_all('courseevt', c.te_group):
                # TODO: Use configured values to create description.
                canvas_event = canvas.create_event(
                    {
                        'context_code': f'course_{c.canvas_group}',
                        'title': r['activity']['activity.id'],
                        'location_name': r['room']['room.name'],
                        'description': '<br>'.join(
                            [
                                r['courseevt']['courseevt.coursename'],
                                r['person_staff']['person.fullname'],
                            ]
                        ),
                        'start_at': r['start_at'],
                        'end_at': r['end_at'],
                    }
                )

                if not canvas_event:
                    break

                session.add(
                    Event(
                        te_id=r['id'],
                        canvas_id=canvas_event.id,
                        te_group=c.te_group,
                        canvas_group=c.canvas_group,
                    )
                )
