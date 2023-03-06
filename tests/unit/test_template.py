import pytest

from fauna.template import FaunaTemplate


def test_templates_with_variables(subtests):

    with subtests.test(msg="single variable template"):
        template = FaunaTemplate("""let x = ${my_var}""")
        expanded = [p for p in template.iter()]
        assert expanded == [("let x = ", "my_var")]

    with subtests.test(msg="duplicate variable template"):
        template = FaunaTemplate("""let x = ${my_var}
let y = ${my_var}
x * y""")
        expanded = [p for p in template.iter()]
        assert expanded == [
            ("let x = ", "my_var"),
            ('\nlet y = ', 'my_var'),
            ('\nx * y', None),
        ]

    with subtests.test(msg="variable at start of template"):
        template = FaunaTemplate("""${my_var} { .name }""")
        expanded = [p for p in template.iter()]
        assert expanded == [
            (None, "my_var"),
            (" { .name }", None),
        ]


def test_templates_with_escapes(subtests):

    with subtests.test(msg="escaped variable template expansion"):
        template = FaunaTemplate("""let x = '$${not_a_var}'""")
        expanded = [p for p in template.iter()]
        assert expanded == [
            ("let x = '$", None),
            ("{not_a_var}'", None),
        ]


def test_templates_with_unsupported_identifiers(subtests):

    with subtests.test(msg="variable with unsupported unicode"):
        template = FaunaTemplate("""let x = ${かわいい}""")
        err_msg = "Invalid placeholder in template: line 1, col 9"
        with pytest.raises(ValueError, match=err_msg):
            _ = [p for p in template.iter()]
