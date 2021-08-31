import os

import zeep

try:
    wsdl = os.environ['TE_WSDL_URL']
    cert = os.environ['TE_CERT']
    username = os.environ['TE_USERNAME']
    password = os.environ['TE_PASSWORD']
except Exception as e:
    logger.debug(f'Failed to load configuration: {e}')
    sys.exit(-1)


client = zeep.Client(wsdl)
key = client.service.register(cert).applicationkey


def course_instances():
    """Get all course instances."""
    n = client.service.findObjects(
        login={
            'username': username,
            'password': password,
            'applicationkey': key,
        },
        type='courseevt',
        numberofobjects=1,
    ).totalnumberofobjects

    num_pages = -(-n // 1000)

    res = []
    for i in range(num_pages):
        page = client.service.findObjects(
            login={
                'username': username,
                'password': password,
                'applicationkey': key,
            },
            type='courseevt',
            numberofobjects=1000,
            beginindex=i * 1000,
        )['objects']['object']
        res += page
    return res


def reservations(instance_id):
    """Get all reservations for a given course instance."""
    n = client.service.findReservations(
        login={
            'username': username,
            'password': password,
            'applicationkey': key,
        },
        searchobjects={'object': [{'type': 'courseevt', 'extid': instance_id}]},
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
            searchobjects={
                'object': [{'type': 'courseevt', 'extid': instance_id}]
            },
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
                ]
            },
            numberofreservations=1000,
            beginindex=i * 1000,
        )['reservations']['reservation']
        res += page
    return res
