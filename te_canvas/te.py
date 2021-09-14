from datetime import datetime
import os
import sys

import zeep

from te_canvas.log import get_logger
from requests.exceptions import ConnectionError

logger = get_logger()

try:
    wsdl = os.environ['TE_WSDL_URL']
    cert = os.environ['TE_CERT']
    username = os.environ['TE_USERNAME']
    password = os.environ['TE_PASSWORD']
except Exception as e:
    logger.debug(f'Failed to load configuration: {e}')
    sys.exit(-1)


try:
    client = zeep.Client(wsdl)
    key = client.service.register(cert).applicationkey
except ConnectionError:
    logger.error(f'TimeEdit connection to "{wsdl}" failed, exiting.')
    sys.exit(-1)


# TODO: Add returnFields parameter, populate from getAlFields?
def get_objects(type, number_of_objects, begin_index):
    """Get max 1000 objects of a given type."""
    res = client.service.findObjects(
        login={
            'username': username,
            'password': password,
            'applicationkey': key,
        },
        type=type,
        numberofobjects=number_of_objects,
        beginindex=begin_index,
    )['objects']['object']
    return list(map(unpack_object, res))


def get_objects_all(type):
    """Get all objects of a given type."""
    n = client.service.findObjects(
        login={
            'username': username,
            'password': password,
            'applicationkey': key,
        },
        type=type,
        numberofobjects=1,
    ).totalnumberofobjects

    num_pages = -(-n // 1000)

    res = []
    for i in range(num_pages):
        page = get_objects(type, 1000, i * 1000)
        res += page
    return res


def unpack_object(o):
    res = {'id': o['extid']}
    for f in o['fields']['field']:
        res[f['extid']] = f['value'][0]
    return res


def get_reservations_all(type, id):
    """Get all reservations for a given object."""
    n = client.service.findReservations(
        login={
            'username': username,
            'password': password,
            'applicationkey': key,
        },
        searchobjects={'object': [{'type': type, 'extid': id}]},
        numberofreservations=1,
    ).totalnumberofreservations

    num_pages = -(-n // 1000)

    res = []
    for i in range(num_pages):
        page = client.service.findReservations(
            login={
                'username': username,
                'password': password,
                'applicationkey': key,
            },
            searchobjects={'object': [{'type': type, 'extid': id}]},
            # TODO: Returntypes should be configurable. Some base values should
            # be used for title and location, configurable values should be
            # concatenated to form event description. Configure this from web
            # interface for connections.
            # TODO: Use English (e.g. `courseevt.coursename_eng`) for some
            # users? Or configurable for entire course instance.
            returntypes={
                'typefield': [
                    {
                        'type': 'person_staff',
                        'field': ['person.id', 'person.fullname'],
                    },
                    {
                        'type': 'courseevt',
                        'field': [
                            'courseevt.uniqueid',
                            'courseevt.coursename',
                            'courseevt.coursename_eng',
                        ],
                    },
                    {'type': 'activity', 'field': ['activity.id']},
                    {'type': 'room', 'field': ['room.name']},
                ]
            },
            numberofreservations=1000,
            beginindex=i * 1000,
        )['reservations']['reservation']
        res += page
    return list(map(unpack_reservation, res))


def unpack_reservation(r):
    date_format = '%Y%m%dT%H%M%S'
    res = {
        'id': r['id'],
        'start_at': datetime.strptime(r['begin'], date_format),
        'end_at': datetime.strptime(r['end'], date_format),
        'length': r['length'],
        'modified': r['modified'],
    }
    for o in r['objects']['object']:
        type, fields = unpack_fields(o)
        res[type] = fields
    return res


def unpack_fields(object: dict) -> (str, dict[str, str]):
    """Takes a TimeEdit `object`. Return the object `type` and all its fields packed in a dict."""
    res = {}
    res['id'] = object['extid']
    for f in object['fields']['field']:
        # NOTE: Assumption that there is only one value per field
        res[f['extid']] = f['value'][0]
    return object['type'], res
