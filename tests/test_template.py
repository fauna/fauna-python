from fauna.template import FaunaTemplate


def test_templates_with_variables(subtests):
    with subtests.test(msg="single variable template expansion"):
        template = FaunaTemplate("""let x = $my_var""")
        expanded = [p for p in template.expand()]
        assert expanded == [("let x = ", "my_var")]
    with subtests.test(msg="duplicate variable template expansion"):
        template = FaunaTemplate("""let x = $my_var
let y = $my_var
x * y""")
        expanded = [p for p in template.expand()]
        assert expanded == [("let x = ", "my_var"), ('\nlet y = ', 'my_var'),
                            ('\nx * y', None)]


def test_templates_with_escapes(subtests):
    with subtests.test(msg="escaped variable template expansion"):
        template = FaunaTemplate("""let x = '$$not_a_var'""")
        expanded = [p for p in template.expand()]
        assert expanded == [("let x = '$", None), ("not_a_var'", None)]
