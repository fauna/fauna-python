from datetime import date
from typing import Any

from fauna.query_builder import fql, QueryInterpolation, LiteralFragment, ValueFragment


def assert_builders(expected: Any, actual: Any):
    if not (isinstance(expected, QueryInterpolation)
            and isinstance(actual, QueryInterpolation)):
        return False

    efs = expected.fragments
    afs = actual.fragments

    for i, f in enumerate(efs):
        if isinstance(f.get(), QueryInterpolation):
            assert_builders(f.get(), afs[i].get())
        assert f.get() == afs[i].get()

    assert len(efs) == len(afs)


def test_query_builder_strings(subtests):
    with subtests.test(msg="pure string query"):
        actual = fql("let x = 11")
        expected = QueryInterpolation([LiteralFragment("let x = 11")])
        assert_builders(expected, actual)

    with subtests.test(msg="pure string query with braces"):
        actual = fql("let x = { y: 11 }")
        expected = QueryInterpolation([LiteralFragment("let x = { y: 11 }")])
        assert_builders(expected, actual)


def test_query_builder_supports_fauna_interpolated_strings():
    actual = fql("""let age = ${n1}\n\"Alice is #{age} years old.\"""", n1=5)
    expected = QueryInterpolation([
        LiteralFragment("let age = "),
        ValueFragment(5),
        LiteralFragment("\n\"Alice is #{age} years old.\""),
    ])

    assert_builders(expected, actual)


def test_query_builder_values(subtests):
    with subtests.test(msg="simple value"):
        user = {"name": "Dino", "age": 0, "birthdate": date(2023, 2, 24)}
        actual = fql("""let x = ${my_var}""", my_var=user)
        expected = QueryInterpolation([
            LiteralFragment("let x = "),
            ValueFragment(user),
        ])

        assert_builders(expected, actual)


def test_query_builder_sub_queries(subtests):
    with subtests.test(msg="single subquery with object"):
        user = {"name": "Dino", "age": 0, "birthdate": date(2023, 2, 24)}
        inner = fql("""let x = ${my_var}""", my_var=user)
        actual = fql("${inner}\nx { .name }", inner=inner)
        expected = QueryInterpolation([
            ValueFragment(inner),
            LiteralFragment("\nx { .name }"),
        ])

        assert_builders(expected, actual)
