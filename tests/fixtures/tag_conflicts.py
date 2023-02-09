from datetime import date, datetime, timezone, timedelta

from fauna.models import Module, DocumentReference

# These keys conflict with types backed by built-ins
conflicts_with_built_ins = {
    "@date": date(2022, 12, 1),
    "@time": datetime(2022, 12, 2, 2, tzinfo=timezone(timedelta(0), '+00:00')),
    "@int": 1,
    "@long": 9999999999999,
    "@double": 1.99,
}
conflicts_with_built_ins_typed_json = '{"@object": {"@date": {"@date": "2022-12-01"}, "@time": {"@time": "2022-12-02T02:00:00+00:00"}, "@int": {"@int": "1"}, "@long": {"@long": "9999999999999"}, "@double": {"@double": "1.99"}}}'
conflicts_with_built_ins_typed = {
    '@object': {
        '@date': {
            '@date': '2022-12-01'
        },
        '@double': {
            '@double': '1.99'
        },
        '@int': {
            '@int': '1'
        },
        '@long': {
            '@long': '9999999999999'
        },
        '@time': {
            '@time': '2022-12-02T02:00:00+00:00'
        }
    }
}

# These keys conflict with types backed by custom classes
conflicts_with_fauna = {
    "@mod": Module("mod"),
    "@doc": DocumentReference("User", "123")
}
conflicts_with_fauna_typed = {
    '@object': {
        '@mod': {
            '@mod': 'mod'
        },
        '@doc': {
            '@doc': 'User:123'
        }
    }
}
conflicts_with_fauna_typed_json = '{"@object": {"@mod": {"@mod": "mod"}, "@doc": {"@doc": "User:123"}}}'

# This key conflicts with object
conflicts_with_object = {"@object": {"name": "Cleve"}}
conflicts_with_object_typed = {"@object": {"@object": {"name": "Cleve"}}}
conflicts_with_object_typed_json = '{"@object": {"@object": {"name": "Cleve"}}}'

# Nested conflicts
nested_conflicts = {
    "@date": {
        "@date": {
            "@time":
            datetime(2022, 12, 2, 2, tzinfo=timezone(timedelta(0), '+00:00'))
        }
    }
}
nested_conflicts_typed = {
    '@object': {
        '@date': {
            '@object': {
                '@date': {
                    '@object': {
                        '@time': {
                            '@time': '2022-12-02T02:00:00+00:00'
                        }
                    }
                }
            }
        }
    }
}
nested_conflicts_typed_json = '{"@object": {"@date": {"@object": {"@date": {"@object": {"@time": {"@time": "2022-12-02T02:00:00+00:00"}}}}}}}'
