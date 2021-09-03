import te_canvas.canvas as canvas
import te_canvas.log as log
import te_canvas.te as te
from te_canvas.db.session import sqla_session
from te_canvas.db.model import Connection, Event

logger = log.get_logger()


def sync_job():
    with sqla_session() as session:
        for (te_group, canvas_group) in session.query(
            Connection.te_group, Connection.canvas_group
        ):
            logger.info(
                f'Syncing from TimeEdit: {te_group} to Canvas: {canvas_group}'
            )

            # Remove all events previously added by us
            for row in session.query(Event).filter(
                Event.te_group == te_group
                and Event.canvas_group == canvas_group
            ):
                canvas.delete_event(row.canvas_id)

            # Clear database
            session.query(Event).filter(
                Event.te_group == te_group
                and Event.canvas_group == canvas_group
            ).delete()

            # Push to Canvas and add to database
            for r in te.reservations(te_group):
                # TODO: Use configured values to create description.
                canvas_event = canvas.create_event(
                    {
                        'context_code': f'course_{canvas_group}',
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
                print(canvas_event.description)
                session.add(
                    Event(
                        te_id=r['id'],
                        canvas_id=canvas_event.id,
                        te_group=te_group,
                        canvas_group=canvas_group,
                    )
                )
