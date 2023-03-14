from datetime import date, datetime, timezone, timedelta

import pytest

from fauna import Module, DocumentReference


@pytest.fixture
def complex_untyped_object():
    return {
        "bugs_coll":
        Module("Bugs"),
        "bug":
        DocumentReference.from_string("Bugs:123"),
        "name":
        "fir",
        "age":
        200,
        "birthdate":
        date(1823, 2, 8),
        "molecules":
        999999999999999999,
        "circumference":
        3.82,
        "created_at":
        datetime(2003,
                 2,
                 8,
                 13,
                 28,
                 12,
                 555,
                 tzinfo=timezone(timedelta(0), '+00:00')),
        "extras": {
            "nest": {
                "num_sticks": 58,
                "@object": {
                    "egg": {
                        "fertilized": False,
                    },
                },
            },
        },
        "measurements": [
            {
                "id":
                1,
                "employee":
                3,
                "time":
                datetime(2013,
                         2,
                         8,
                         12,
                         00,
                         5,
                         123,
                         tzinfo=timezone(timedelta(0), '+00:00'))
            },
            {
                "id":
                2,
                "employee":
                5,
                "time":
                datetime(2023,
                         2,
                         8,
                         14,
                         22,
                         1,
                         1,
                         tzinfo=timezone(timedelta(0), '+00:00'))
            },
        ]
    }


@pytest.fixture
def complex_typed_object():
    return {
        'bugs_coll': {
            '@mod': 'Bugs'
        },
        'bug': {
            '@doc': 'Bugs:123'
        },
        'name':
        'fir',
        'age': {
            '@int': '200'
        },
        'birthdate': {
            '@date': '1823-02-08'
        },
        'molecules': {
            '@long': '999999999999999999'
        },
        'circumference': {
            '@double': '3.82'
        },
        'created_at': {
            '@time': '2003-02-08T13:28:12.000555+00:00'
        },
        'extras': {
            'nest': {
                '@object': {
                    '@object': {
                        'egg': {
                            'fertilized': False
                        }
                    },
                    'num_sticks': {
                        '@int': '58'
                    },
                }
            }
        },
        'measurements': [{
            'id': {
                '@int': '1'
            },
            'employee': {
                '@int': '3'
            },
            'time': {
                '@time': '2013-02-08T12:00:05.000123+00:00'
            }
        }, {
            'id': {
                '@int': '2'
            },
            'employee': {
                '@int': '5'
            },
            'time': {
                '@time': '2023-02-08T14:22:01.000001+00:00'
            }
        }]
    }
