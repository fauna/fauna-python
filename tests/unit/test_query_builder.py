from datetime import date

from fauna.query_builder import fql


def test_query_builder_strings(subtests):
    with subtests.test(msg="pure string query"):
        q = fql("""let x = 11""")
        r = q.to_query()
        assert r == {"fql": ["let x = 11"]}

    with subtests.test(msg="pure string query with braces"):
        q = fql("""let x = { y: 11 }""")
        r = q.to_query()
        assert r == {"fql": ["let x = { y: 11 }"]}


def test_query_builder_supports_fauna_interpolated_strings():
    q = fql("""let age = ${n1}\n\"Alice is #{age} years old.\"""", n1=5)
    r = q.to_query()
    assert r == {
        "fql": [
            "let age = ",
            {
                "value": {
                    "@int": "5"
                }
            },
            "\n\"Alice is #{age} years old.\"",
        ]
    }


def test_query_builder_values(subtests):
    with subtests.test(msg="simple value"):
        user = {"name": "Dino", "age": 0, "birthdate": date(2023, 2, 24)}
        q = fql("""let x = ${my_var}""", my_var=user)
        r = q.to_query()
        assert r == {
            "fql": [
                "let x = ", {
                    'value': {
                        'name': 'Dino',
                        'age': {
                            '@int': '0'
                        },
                        'birthdate': {
                            '@date': '2023-02-24'
                        }
                    }
                }
            ]
        }


def test_query_builder_sub_queries(subtests):
    with subtests.test(msg="single subquery with object"):
        user = {"name": "Dino", "age": 0, "birthdate": date(2023, 2, 24)}
        inner = fql("""let x = ${my_var}""", my_var=user)
        outer = fql("""${inner}
x { .name }""", inner=inner)

        r = outer.to_query()

        assert r == {
            "fql": [{
                "fql": [
                    "let x = ", {
                        'value': {
                            'name': 'Dino',
                            'age': {
                                '@int': '0'
                            },
                            'birthdate': {
                                '@date': '2023-02-24'
                            }
                        }
                    }
                ]
            }, "\nx { .name }"]
        }
