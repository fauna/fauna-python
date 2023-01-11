import sys
from datetime import datetime
from unittest import TestCase
import iso8601

from faunadb import query
from faunadb.objects import Ref, SetRef, FaunaTime, Query, Native
from faunadb._json import to_json


class SerializationTest(TestCase):

    def test_native(self):
        self.assertJson(Native.COLLECTIONS, '{"@ref":{"id":"collections"}}')
        self.assertJson(Native.INDEXES, '{"@ref":{"id":"indexes"}}')
        self.assertJson(Native.DATABASES, '{"@ref":{"id":"databases"}}')
        self.assertJson(Native.FUNCTIONS, '{"@ref":{"id":"functions"}}')
        self.assertJson(Native.KEYS, '{"@ref":{"id":"keys"}}')
        self.assertJson(Native.ACCESS_PROVIDERS,
                        '{"@ref":{"id":"access_providers"}}')

    def test_ref(self):
        self.assertJson(Ref("collections"), '{"@ref":{"id":"collections"}}')
        self.assertJson(
            Ref("widgets", Native.COLLECTIONS),
            '{"@ref":{"collection":{"@ref":{"id":"collections"}},"id":"widgets"}}'
        )

    def test_set_ref(self):
        self.assertJson(
            SetRef({
                "match": Ref("widgets", Native.INDEXES),
                "terms": "Laptop"
            }),
            ('{'
             '"@set":{'
             '"match":{"@ref":{"collection":{"@ref":{"id":"indexes"}},"id":"widgets"}},'
             '"terms":"Laptop"'
             '}'
             '}'))

    def test_fauna_time(self):
        self.assertJson(FaunaTime('1970-01-01T00:00:00.123456789Z'),
                        '{"@ts":"1970-01-01T00:00:00.123456789Z"}')
        self.assertJson(datetime.fromtimestamp(0, iso8601.UTC),
                        '{"@ts":"1970-01-01T00:00:00Z"}')

    def test_bytes(self):
        self.assertJson(bytearray(b'\x01\x02\x03'), '{"@bytes":"AQID"}')
        if sys.version_info.major == 3:
            # In Python 3.x we should also accept bytes
            self.assertJson(b'\x01\x02\x03', '{"@bytes":"AQID"}')

    def test_query(self):
        expected1 = '{"@query":{"expr":{"var":"x"},"lambda":"x"}}'
        expected2 = '{"@query":{"api_version":"3","expr":{"var":"x"},"lambda":"x"}}'
        self.assertJson(Query({
            "lambda": "x",
            "expr": {
                "var": "x"
            }
        }), expected1)
        self.assertJson(
            Query({
                "api_version": "3",
                "lambda": "x",
                "expr": {
                    "var": "x"
                }
            }), expected2)

    #region Basic forms

    def test_abort(self):
        self.assertJson(query.abort("aborting"), '{"abort":"aborting"}')

    def test_at(self):
        self.assertJson(
            query.at(datetime.fromtimestamp(0, iso8601.UTC),
                     query.get(query.index("widgets"))),
            '{"at":{"@ts":"1970-01-01T00:00:00Z"},"expr":{"get":{"index":"widgets"}}}'
        )

    def test_let(self):
        self.assertJson(query.let({"x": 1}, 1), '{"in":1,"let":[{"x":1}]}')

    def test_vars(self):
        self.assertJson(query.var("x"), '{"var":"x"}')

    def test_if_expr(self):
        self.assertJson(query.if_(True, "true", "false"),
                        '{"else":"false","if":true,"then":"true"}')

    def test_do(self):
        self.assertJson(query.do(query.add(1, 2), query.var("x")),
                        '{"do":[{"add":[1,2]},{"var":"x"}]}')
        self.assertJson(query.do(1), '{"do":[1]}')
        self.assertJson(query.do(1, 2), '{"do":[1,2]}')
        self.assertJson(query.do([1, 2]), '{"do":[[1,2]]}')

    def test_lambda_query(self):
        #pylint: disable=unnecessary-lambda
        self.assertJson(query.lambda_query(lambda a: a),
                        '{"expr":{"var":"a"},"lambda":"a"}')
        self.assertJson(
            query.lambda_query(lambda a, b: query.add(a, b)),
            '{"expr":{"add":[{"var":"a"},{"var":"b"}]},"lambda":["a","b"]}')

    def test_lambda_expr(self):
        self.assertJson(query.lambda_("a", query.var("a")),
                        '{"expr":{"var":"a"},"lambda":"a"}')
        self.assertJson(
            query.lambda_(["a", "b"], query.add(query.var("a"),
                                                query.var("b"))),
            '{"expr":{"add":[{"var":"a"},{"var":"b"}]},"lambda":["a","b"]}')

    #endregion

    #region Collection functions

    def test_map_expr(self):
        self.assertJson(
            query.map_(lambda a: a, [1, 2, 3]),
            '{"collection":[1,2,3],"map":{"expr":{"var":"a"},"lambda":"a"}}')

    def test_foreach(self):
        self.assertJson(
            query.foreach(lambda a: a, [1, 2, 3]),
            '{"collection":[1,2,3],"foreach":{"expr":{"var":"a"},"lambda":"a"}}'
        )

    def test_filter_expr(self):
        self.assertJson(
            query.filter_(lambda a: a, [True, False, True]),
            '{"collection":[true,false,true],"filter":{"expr":{"var":"a"},"lambda":"a"}}'
        )

    def test_take(self):
        self.assertJson(query.take(2, [1, 2, 3]),
                        '{"collection":[1,2,3],"take":2}')

    def test_drop(self):
        self.assertJson(query.drop(2, [1, 2, 3]),
                        '{"collection":[1,2,3],"drop":2}')

    def test_prepend(self):
        self.assertJson(query.prepend([1, 2], [3, 4]),
                        '{"collection":[3,4],"prepend":[1,2]}')

    def test_append(self):
        self.assertJson(query.append([1, 2], [3, 4]),
                        '{"append":[1,2],"collection":[3,4]}')

    def test_is_empty(self):
        self.assertJson(query.is_empty([1, 2]), '{"is_empty":[1,2]}')

    def test_is_nonempty(self):
        self.assertJson(query.is_nonempty([1, 2]), '{"is_nonempty":[1,2]}')

    #endregion

    #region Read functions

    def test_get(self):
        self.assertJson(query.get(query.collection("widget")),
                        '{"get":{"collection":"widget"}}')
        self.assertJson(query.get(query.collection("widget"), ts=123),
                        '{"get":{"collection":"widget"},"ts":123}')

    def test_paginate(self):
        self.assertJson(query.paginate(query.collection("widget")),
                        '{"paginate":{"collection":"widget"}}')
        self.assertJson(
            query.paginate(query.collection("widget"),
                           size=1,
                           ts=123,
                           after=query.ref(query.collection("widget"), "1"),
                           before=query.ref(query.collection("widget"), "10"),
                           events=True,
                           sources=True),
            ('{"after":{"id":"1","ref":{"collection":"widget"}},'
             '"before":{"id":"10","ref":{"collection":"widget"}},'
             '"events":true,"paginate":{"collection":"widget"},'
             '"size":1,"sources":true,"ts":123}'))

    def test_exists(self):
        self.assertJson(query.exists(query.collection("widget")),
                        '{"exists":{"collection":"widget"}}')
        self.assertJson(query.exists(query.collection("widget"), ts=123),
                        '{"exists":{"collection":"widget"},"ts":123}')

    #endregion

    #region Write functions

    def test_create(self):
        json = ('{"create":{"collection":"widget"},'
                '"params":{"object":{"data":{"object":{"name":"Laptop"}}}}}')
        self.assertJson(
            query.create(query.collection("widget"),
                         {"data": {
                             "name": "Laptop"
                         }}), json)

    def test_update(self):
        json = ('{"params":{"object":{"data":{"object":{"name":"Laptop"}}}},'
                '"update":{"collection":"widget"}}')
        self.assertJson(
            query.update(query.collection("widget"),
                         {"data": {
                             "name": "Laptop"
                         }}), json)

    def test_replace(self):
        json = ('{"params":{"object":{"data":{"object":{"name":"Laptop"}}}},'
                '"replace":{"collection":"widget"}}')
        self.assertJson(
            query.replace(query.collection("widget"),
                          {"data": {
                              "name": "Laptop"
                          }}), json)

    def test_delete(self):
        self.assertJson(query.delete(query.collection("widget")),
                        '{"delete":{"collection":"widget"}}')

    def test_insert(self):
        json = (
            '{"action":"create","insert":{"collection":"widget"},'
            '"params":{"object":{"data":{"object":{"name":"Laptop"}}}},"ts":123}'
        )
        self.assertJson(
            query.insert(query.collection("widget"),
                         ts=123,
                         action="create",
                         params={"data": {
                             "name": "Laptop"
                         }}), json)

    def test_remove(self):
        self.assertJson(
            query.remove(query.collection("widget"), ts=123, action="create"),
            '{"action":"create","remove":{"collection":"widget"},"ts":123}')

    def test_create_collection(self):
        self.assertJson(query.create_collection({"name": "widget"}),
                        '{"create_collection":{"object":{"name":"widget"}}}')

    def test_create_database(self):
        self.assertJson(query.create_database({"name": "db-name"}),
                        '{"create_database":{"object":{"name":"db-name"}}}')

    def test_create_index(self):
        self.assertJson(
            query.create_index({
                "name": "index-name",
                "source": query.collection("widget")
            }),
            '{"create_index":{"object":{"name":"index-name","source":{"collection":"widget"}}}}'
        )

    def test_create_key(self):
        self.assertJson(
            query.create_key({
                "database": query.database("db-name"),
                "role": "client"
            }),
            '{"create_key":{"object":{"database":{"database":"db-name"},"role":"client"}}}'
        )

    def test_create_role(self):
        self.assertJson(
            query.create_role({
                "name": "a_role",
                "privileges": {
                    "resource": query.collections(),
                    "actions": {
                        "read": True
                    }
                }
            }),
            '{"create_role":{"object":{"name":"a_role","privileges":{"object":{"actions":{"object":{"read":true}},"resource":{"collections":null}}}}}}'
        )

    def test_create_access_provider(self):
        providerName = 'provider_'
        issuerName = 'issuer_'
        jwksUri = 'https://auth.fauna.com/somewhere'
        self.assertJson(
            query.create_access_provider({
                "name": providerName,
                "issuer": issuerName,
                "jwks_uri": jwksUri
            }),
            '{"create_access_provider":{"object":{"issuer":"' + issuerName +
            '","jwks_uri":"' + jwksUri + '","name":"' + providerName + '"}}}')

    def test_move_database(self):
        q = query.move_database(query.database("src-db"),
                                query.database("dest-db"))
        self.assertJson(
            q,
            '{"move_database":{"database":"src-db"},"to":{"database":"dest-db"}}'
        )

    #endregion

    #region Sets

    def test_singleton(self):
        self.assertJson(
            query.singleton(query.ref(query.collection("widget"), "1")),
            '{"singleton":{"id":"1","ref":{"collection":"widget"}}}')

    def test_events(self):
        self.assertJson(
            query.events(query.ref(query.collection("widget"), "1")),
            '{"events":{"id":"1","ref":{"collection":"widget"}}}')
        self.assertJson(query.events(query.match(query.index("widget"))),
                        '{"events":{"match":{"index":"widget"}}}')

    def test_match(self):
        self.assertJson(query.match(query.index("widget")),
                        '{"match":{"index":"widget"}}')
        self.assertJson(query.match(query.index("widget"), "Laptop"),
                        '{"match":{"index":"widget"},"terms":"Laptop"}')

    def test_merge(self):
        self.assertJson(
            query.merge({"x": 24}, {"y": 25}),
            '{"merge":{"object":{"x":24}},"with":{"object":{"y":25}}}')
        self.assertJson(
            query.merge({"points": 900}, {"name": "Trevor"}),
            '{"merge":{"object":{"points":900}},"with":{"object":{"name":"Trevor"}}}'
        )
        self.assertJson(query.merge({}, {"id": 9}),
                        '{"merge":{"object":{}},"with":{"object":{"id":9}}}')
        self.assertJson(
            query.merge({"x": 24}, {"y": 25}, lambda key, left, right: right),
            '{"lambda":{"expr":{"var":"right"},"lambda":["key","left","right"]},"merge":{"object":{"x":24}},"with":{"object":{"y":25}}}'
        )

    def test_reverse(self):
        self.assertJson(query.reverse([1, 2, 3]), '{"reverse":[1,2,3]}')

    def test_union(self):
        self.assertJson(query.union(), '{"union":[]}')
        self.assertJson(query.union(query.index("widget")),
                        '{"union":{"index":"widget"}}')
        self.assertJson(
            query.union(query.index("widget"), query.index("things")),
            '{"union":[{"index":"widget"},{"index":"things"}]}')

    def test_reduce(self):
        expected = '{"collection":[1,2,3,4,5,6,7,8,9],"initial":0,"reduce":{"expr":{"add":[{"var":"accum"},{"var":"val"}]},"lambda":["accum","val"]}}'
        col = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        lambda_ = query.lambda_query(lambda accum, val: query.add(accum, val))
        initial = 0
        self.assertJson(query.reduce(lambda_, initial, col), expected)

    def test_intersection(self):
        self.assertJson(query.intersection(), '{"intersection":[]}')
        self.assertJson(query.intersection(query.index("widget")),
                        '{"intersection":{"index":"widget"}}')
        self.assertJson(
            query.intersection(query.index("widget"), query.index("things")),
            '{"intersection":[{"index":"widget"},{"index":"things"}]}')

    def test_difference(self):
        self.assertJson(query.difference(), '{"difference":[]}')
        self.assertJson(query.difference(query.index("widget")),
                        '{"difference":{"index":"widget"}}')
        self.assertJson(
            query.difference(query.index("widget"), query.index("things")),
            '{"difference":[{"index":"widget"},{"index":"things"}]}')

    def test_distinct(self):
        self.assertJson(
            query.distinct(SetRef({"match": query.index("widget")})),
            '{"distinct":{"@set":{"match":{"index":"widget"}}}}')

    def test_join(self):
        self.assertJson(
            query.join(query.match(query.index("widget")),
                       query.index("things")),
            '{"join":{"match":{"index":"widget"}},"with":{"index":"things"}}')

    def test_range(self):
        self.assertJson(
            query.range(
                query.match(
                    query.ref("indexes/spellbooks_by_owner"),
                    query.ref("collections/characters/104979509695139637")),
                10,
                50,
            ),
            '{"from":10,"range":{"match":{"@ref":"indexes/spellbooks_by_owner"},"terms":{"@ref":"collections/characters/104979509695139637"}},"to":50}'
        )

    #endregion

    #region Authentication

    def test_login(self):
        self.assertJson(
            query.login(query.ref(query.collection("widget"), "1"),
                        {"password": "abracadabra"}),
            '{"login":{"id":"1","ref":{"collection":"widget"}},"params":{"object":{"password":"abracadabra"}}}'
        )

    def test_logout(self):
        self.assertJson(query.logout(True), '{"logout":true}')

    def test_identify(self):
        self.assertJson(
            query.identify(query.ref(query.collection("widget"), "1"),
                           "abracadabra"),
            '{"identify":{"id":"1","ref":{"collection":"widget"}},"password":"abracadabra"}'
        )

    def test_identity(self):
        self.assertJson(query.identity(), '{"identity":null}')

    def test_current_token(self):
        self.assertJson(query.current_token(), '{"current_token":null}')

    def test_current_identity(self):
        self.assertJson(query.current_identity(), '{"current_identity":null}')

    def test_has_identity(self):
        self.assertJson(query.has_identity(), '{"has_identity":null}')

    def test_has_current_identity(self):
        self.assertJson(query.has_current_identity(),
                        '{"has_current_identity":null}')

    def test_has_current_token(self):
        self.assertJson(query.has_current_token(),
                        '{"has_current_token":null}')

    #endregion

    #region String functions

    def test_format(self):
        self.assertJson(
            query.format("%s %d and then %.2f", 'Hey there', 2019, 3.14),
            '{"format":"%s %d and then %.2f","values":["Hey there",2019,3.14]}'
        )
        self.assertJson(query.format("always 100%%"),
                        '{"format":"always 100%%","values":[]}')

    def test_concat(self):
        self.assertJson(query.concat(["a", "b"]), '{"concat":["a","b"]}')
        self.assertJson(query.concat(["a", "b"], "/"),
                        '{"concat":["a","b"],"separator":"/"}')

    def test_casefold(self):
        self.assertJson(query.casefold("a string"), '{"casefold":"a string"}')
        self.assertJson(query.casefold("a string", "NFD"),
                        '{"casefold":"a string","normalizer":"NFD"}')

    def test_starts_with(self):
        self.assertJson(query.starts_with("faunadb", "fauna"),
                        '{"search":"fauna","startswith":"faunadb"}')

    def test_ends_with(self):
        self.assertJson(query.ends_with("faunadb", "db"),
                        '{"endswith":"faunadb","search":"db"}')

    def test_contains_str(self):
        self.assertJson(query.contains_str("faunadb", "db"),
                        '{"containsstr":"faunadb","search":"db"}')

    def test_contains_str_regex(self):
        self.assertJson(query.contains_str_regex("faunadb", "f(.*)db"),
                        '{"containsstrregex":"faunadb","pattern":"f(.*)db"}')

    def regex_escape(self):
        self.assertJson(query.regex_escape("f[a](.*)db"),
                        '{"regexescape":"f[a](.*)db"}')

    def test_ngram(self):
        self.assertJson(query.ngram("str"), '{"ngram":"str"}')
        self.assertJson(query.ngram(["str0", "str1"]),
                        '{"ngram":["str0","str1"]}')
        self.assertJson(query.ngram("str", min=2, max=3),
                        '{"max":3,"min":2,"ngram":"str"}')
        self.assertJson(query.ngram(["str0", "str1"], min=2, max=3),
                        '{"max":3,"min":2,"ngram":["str0","str1"]}')

    def test_find_str(self):
        self.assertJson(query.find_str("ABC", "A"),
                        '{"find":"A","findstr":"ABC"}')

    def test_find_str_regex(self):
        self.assertJson(
            query.find_str_regex("one fish two Fish", "[fF]ish"),
            '{"findstrregex":"one fish two Fish","pattern":"[fF]ish"}')

    def test_replace_str(self):
        self.assertJson(
            query.replace_str("one fish two Fish", "fish", "dog"),
            '{"find":"fish","replace":"dog","replacestr":"one fish two Fish"}')

    def test_replace_str_regex(self):
        self.assertJson(
            query.replace_str_regex("one fish two Fish", "[fF]ish", "dog"),
            '{"pattern":"[fF]ish","replace":"dog","replacestrregex":"one fish two Fish"}'
        )

    def test_length(self):
        self.assertJson(query.length('hello'), '{"length":"hello"}')

    def test_lowercase(self):
        self.assertJson(query.lowercase('One more photo'),
                        '{"lowercase":"One more photo"}')

    def test_uppercase(self):
        self.assertJson(query.uppercase('guns for hands'),
                        '{"uppercase":"guns for hands"}')

    def test_titlecase(self):
        self.assertJson(query.titlecase("together"),
                        '{"titlecase":"together"}')

    def test_trim(self):
        self.assertJson(query.trim("chlorine"), '{"trim":"chlorine"}')

    def test_ltrim(self):
        self.assertJson(query.ltrim(" car radio "), '{"ltrim":" car radio "}')

    def test_rtrim(self):
        self.assertJson(query.rtrim("mic check "), '{"rtrim":"mic check "}')

    def test_space(self):
        self.assertJson(query.space(34), '{"space":34}')

    def test_substring(self):
        self.assertJson(query.substring("bulawayo", 0, 3),
                        '{"length":3,"start":0,"substring":"bulawayo"}')

    def test_repeat(self):
        self.assertJson(query.repeat("blAH", 5),
                        '{"number":5,"repeat":"blAH"}')

    #endregion

    #region Time and date functions

    def test_time(self):
        self.assertJson(query.time("1970-01-01T00:00:00+00:00"),
                        '{"time":"1970-01-01T00:00:00+00:00"}')

    def test_now(self):
        self.assertJson(query.now(), '{"now":null}')

    def test_epoch(self):
        self.assertJson(query.epoch(1, "second"),
                        '{"epoch":1,"unit":"second"}')
        self.assertJson(query.epoch(1, "milisecond"),
                        '{"epoch":1,"unit":"milisecond"}')
        self.assertJson(query.epoch(1, "microsecond"),
                        '{"epoch":1,"unit":"microsecond"}')
        self.assertJson(query.epoch(1, "nanosecond"),
                        '{"epoch":1,"unit":"nanosecond"}')

    def test_time_add(self):
        self.assertJson(
            query.time_add("1970-01-01T00:00:00+00:00", 1, "hour"),
            '{"offset":1,"time_add":"1970-01-01T00:00:00+00:00","unit":"hour"}'
        )

    def test_time_subtract(self):
        self.assertJson(
            query.time_subtract("1970-01-01T00:00:00+00:00", 1, "day"),
            '{"offset":1,"time_subtract":"1970-01-01T00:00:00+00:00","unit":"day"}'
        )

    def test_time_diff(self):
        self.assertJson(
            query.time_diff("1970-01-01T00:00:00+00:00",
                            query.epoch(1, "second"), "second"),
            '{"other":{"epoch":1,"unit":"second"},"time_diff":"1970-01-01T00:00:00+00:00","unit":"second"}'
        )

    def test_date(self):
        self.assertJson(query.date("1970-01-01"), '{"date":"1970-01-01"}')

    #endregion

    #region Miscellaneous functions

    def test_new_id(self):
        self.assertJson(query.new_id(), '{"new_id":null}')

    def test_database(self):
        self.assertJson(query.database("db-name"), '{"database":"db-name"}')

    def test_index(self):
        self.assertJson(query.index("index-name"), '{"index":"index-name"}')

    def test_collection(self):
        self.assertJson(query.collection("collection-name"),
                        '{"collection":"collection-name"}')

    def test_documents(self):
        self.assertJson(query.documents(query.collection("users")),
                        '{"documents":{"collection":"users"}}')

    def test_role(self):
        self.assertJson(query.role("role-name"), '{"role":"role-name"}')

    def test_access_provider(self):
        self.assertJson(
            query.access_provider("name", query.database("db1")),
            '{"access_provider":"name","scope":{"database":"db1"}}')
        self.assertJson(query.access_provider("name"),
                        '{"access_provider":"name"}')

    def test_access_providers(self):
        self.assertJson(query.access_providers(query.database("db1")),
                        '{"access_providers":{"database":"db1"}}')

    def test_equals(self):
        self.assertJson(query.equals(1), '{"equals":1}')
        self.assertJson(query.equals(1, 2), '{"equals":[1,2]}')
        self.assertJson(query.equals([1, 2]), '{"equals":[1,2]}')

    def test_contains(self):
        json = (
            '{"contains":["favorites","foods"],'
            '"in":{"object":{"favorites":{"object":{"foods":["steak"]}}}}}')
        self.assertJson(
            query.contains(["favorites", "foods"],
                           {"favorites": {
                               "foods": ["steak"]
                           }}), json)

    def test_contains_path(self):
        json = (
            '{"contains_path":["favorites","foods"],'
            '"in":{"object":{"favorites":{"object":{"foods":["steak"]}}}}}')
        self.assertJson(
            query.contains_path(["favorites", "foods"],
                                {"favorites": {
                                    "foods": ["steak"]
                                }}), json)

    def test_contains_value(self):
        json = (
            '{"contains_value":"steak",'
            '"in":{"object":{"favorites":{"object":{"foods":["steak"]}}}}}')
        self.assertJson(
            query.contains_value("steak", {"favorites": {
                "foods": ["steak"]
            }}), json)

    def test_contains_field(self):
        json = (
            '{"contains_field":"favorites",'
            '"in":{"object":{"favorites":{"object":{"foods":["steak"]}}}}}')
        self.assertJson(
            query.contains_field("favorites",
                                 {"favorites": {
                                     "foods": ["steak"]
                                 }}), json)

    def test_select(self):
        json = (
            '{"from":{"object":{"favorites":{"object":{"foods":["steak"]}}}},'
            '"select":["favorites","foods",0]}')
        self.assertJson(
            query.select(["favorites", "foods", 0],
                         {"favorites": {
                             "foods": ["steak"]
                         }}), json)

    def test_select_with_default(self):
        json = (
            '{"default":"no food","from":{"object":{"favorites":{"object":{"foods":["steak"]}}}},'
            '"select":["favorites","foods",0]}')
        self.assertJson(
            query.select_with_default(["favorites", "foods", 0],
                                      {"favorites": {
                                          "foods": ["steak"]
                                      }}, "no food"), json)

    def test_select_all(self):
        json = (
            '{"from":[{"object":{"foo":"bar"}},{"object":{"foo":"baz"}}],"select_all":"foo"}'
        )
        self.assertJson(
            query.select_all("foo", [{
                "foo": "bar"
            }, {
                "foo": "baz"
            }]), json)

    def test_add(self):
        self.assertJson(query.add(1), '{"add":1}')
        self.assertJson(query.add(1, 2, 3), '{"add":[1,2,3]}')
        self.assertJson(query.add([1, 2, 3]), '{"add":[1,2,3]}')

    def test_multiply(self):
        self.assertJson(query.multiply(1), '{"multiply":1}')
        self.assertJson(query.multiply(1, 2, 3), '{"multiply":[1,2,3]}')
        self.assertJson(query.multiply([1, 2, 3]), '{"multiply":[1,2,3]}')

    def test_subtract(self):
        self.assertJson(query.subtract(1), '{"subtract":1}')
        self.assertJson(query.subtract(1, 2, 3), '{"subtract":[1,2,3]}')
        self.assertJson(query.subtract([1, 2, 3]), '{"subtract":[1,2,3]}')

    def test_divide(self):
        self.assertJson(query.divide(1), '{"divide":1}')
        self.assertJson(query.divide(1, 2, 3), '{"divide":[1,2,3]}')
        self.assertJson(query.divide([1, 2, 3]), '{"divide":[1,2,3]}')

    def test_pow(self):
        self.assertJson(query.pow(2, 3), '{"exp":3,"pow":2}')

    def test_max(self):
        self.assertJson(query.max(1, 2), '{"max":[1,2]}')
        self.assertJson(query.max(1, 2, 3), '{"max":[1,2,3]}')
        self.assertJson(query.max([1, 2, 3]), '{"max":[1,2,3]}')

    def test_min(self):
        self.assertJson(query.min(1, 2), '{"min":[1,2]}')
        self.assertJson(query.min(1, 2, 3), '{"min":[1,2,3]}')
        self.assertJson(query.min([1, 2, 3]), '{"min":[1,2,3]}')

    def test_abs(self):
        self.assertJson(query.abs(-10), '{"abs":-10}')

    def test_trunc(self):
        self.assertJson(query.trunc(45), '{"trunc":45}')
        self.assertJson(query.trunc(45, 3), '{"precision":3,"trunc":45}')

    def test_bitor(self):
        self.assertJson(query.bitor(1), '{"bitor":1}')
        self.assertJson(query.bitor(1, 2, 3), '{"bitor":[1,2,3]}')
        self.assertJson(query.bitor([1, 2, 3]), '{"bitor":[1,2,3]}')

    def test_degrees(self):
        self.assertJson(query.degrees(90), '{"degrees":90}')

    def test_cos(self):
        self.assertJson(query.cos(60), '{"cos":60}')

    def test_sqrt(self):
        self.assertJson(query.sqrt(9), '{"sqrt":9}')

    def test_tan(self):
        self.assertJson(query.tan(45), '{"tan":45}')

    def test_tanh(self):
        self.assertJson(query.tanh(45), '{"tanh":45}')

    def test_acos(self):
        self.assertJson(query.acos(0), '{"acos":0}')

    def test_cosh(self):
        self.assertJson(query.cosh(120), '{"cosh":120}')

    def test_hypot(self):
        self.assertJson(query.hypot(9, 0), '{"b":0,"hypot":9}')

    def test_atan(self):
        self.assertJson(query.atan(120), '{"atan":120}')

    def test_log(self):
        self.assertJson(query.log(100), '{"log":100}')

    def test_bitnot(self):
        self.assertJson(query.bitnot(0), '{"bitnot":0}')
        self.assertJson(query.bitnot(1), '{"bitnot":1}')

    def test_bitxor(self):
        self.assertJson(query.bitxor(0, 1), '{"bitxor":[0,1]}')
        self.assertJson(query.bitxor(1, 2, 4), '{"bitxor":[1,2,4]}')

    def test_bitand(self):
        self.assertJson(query.bitand(1, 0), '{"bitand":[1,0]}')
        self.assertJson(query.bitand(7, 3), '{"bitand":[7,3]}')

    def test_ceil(self):
        self.assertJson(query.ceil(67.789), '{"ceil":67.789}')

    def test_asin(self):
        self.assertJson(query.asin(0), '{"asin":0}')

    def test_radians(self):
        self.assertJson(query.radians(45), '{"radians":45}')

    def test_round(self):
        self.assertJson(query.round(123.456), '{"round":123.456}')
        self.assertJson(query.round(123.456, 2),
                        '{"precision":2,"round":123.456}')

    def test_floor(self):
        self.assertJson(query.floor(89.1234), '{"floor":89.1234}')

    def test_sign(self):
        self.assertJson(query.sign(-90), '{"sign":-90}')

    def test_exp(self):
        self.assertJson(query.exp(2.1), '{"exp":2.1}')

    def test_ln(self):
        self.assertJson(query.ln(900), '{"ln":900}')

    def test_any(self):
        self.assertJson(query.any([True, True, True]),
                        '{"any":[true,true,true]}')

    def test_all(self):
        self.assertJson(query.all([True, True, True]),
                        '{"all":[true,true,true]}')

    def test_modulo(self):
        self.assertJson(query.modulo(1), '{"modulo":1}')
        self.assertJson(query.modulo(1, 2, 3), '{"modulo":[1,2,3]}')
        self.assertJson(query.modulo([1, 2, 3]), '{"modulo":[1,2,3]}')

    def test_count(self):
        self.assertJson(query.count([1, 2, 3, 4, 5]), '{"count":[1,2,3,4,5]}')

    def test_sum(self):
        self.assertJson(query.sum([1, 2, 3, 4, 5]), '{"sum":[1,2,3,4,5]}')

    def test_mean(self):
        self.assertJson(query.mean([1, 2, 3, 4, 5]), '{"mean":[1,2,3,4,5]}')

    def test_lt(self):
        self.assertJson(query.lt(1), '{"lt":1}')
        self.assertJson(query.lt(1, 2, 3), '{"lt":[1,2,3]}')
        self.assertJson(query.lt([1, 2, 3]), '{"lt":[1,2,3]}')

    def test_lte(self):
        self.assertJson(query.lte(1), '{"lte":1}')
        self.assertJson(query.lte(1, 2, 3), '{"lte":[1,2,3]}')
        self.assertJson(query.lte([1, 2, 3]), '{"lte":[1,2,3]}')

    def test_gt(self):
        self.assertJson(query.gt(1), '{"gt":1}')
        self.assertJson(query.gt(1, 2, 3), '{"gt":[1,2,3]}')
        self.assertJson(query.gt([1, 2, 3]), '{"gt":[1,2,3]}')

    def test_gte(self):
        self.assertJson(query.gte(1), '{"gte":1}')
        self.assertJson(query.gte(1, 2, 3), '{"gte":[1,2,3]}')
        self.assertJson(query.gte([1, 2, 3]), '{"gte":[1,2,3]}')

    def test_and_expr(self):
        self.assertJson(query.and_(True), '{"and":true}')
        self.assertJson(query.and_(True, False, False),
                        '{"and":[true,false,false]}')
        self.assertJson(query.and_([True, False, False]),
                        '{"and":[true,false,false]}')

    def test_or_expr(self):
        self.assertJson(query.or_(False), '{"or":false}')
        self.assertJson(query.or_(False, True, True),
                        '{"or":[false,true,true]}')
        self.assertJson(query.or_([False, True, True]),
                        '{"or":[false,true,true]}')

    def test_not_expr(self):
        self.assertJson(query.not_(False), '{"not":false}')


#endregion

#region Type functions

    def test_isnumber(self):
        self.assertJson(query.is_number(query.var("x")),
                        '{"is_number":{"var":"x"}}')

    def test_isdouble(self):
        self.assertJson(query.is_double(query.var("x")),
                        '{"is_double":{"var":"x"}}')

    def test_isinteger(self):
        self.assertJson(query.is_integer(query.var("x")),
                        '{"is_integer":{"var":"x"}}')

    def test_isboolean(self):
        self.assertJson(query.is_boolean(query.var("x")),
                        '{"is_boolean":{"var":"x"}}')

    def test_isnull(self):
        self.assertJson(query.is_null(query.var("x")),
                        '{"is_null":{"var":"x"}}')

    def test_isbytes(self):
        self.assertJson(query.is_bytes(query.var("x")),
                        '{"is_bytes":{"var":"x"}}')

    def test_istimestamp(self):
        self.assertJson(query.is_timestamp(query.var("x")),
                        '{"is_timestamp":{"var":"x"}}')

    def test_isdate(self):
        self.assertJson(query.is_date(query.var("x")),
                        '{"is_date":{"var":"x"}}')

    def test_isstring(self):
        self.assertJson(query.is_string(query.var("x")),
                        '{"is_string":{"var":"x"}}')

    def test_isarray(self):
        self.assertJson(query.is_array(query.var("x")),
                        '{"is_array":{"var":"x"}}')

    def test_isobject(self):
        self.assertJson(query.is_object(query.var("x")),
                        '{"is_object":{"var":"x"}}')

    def test_isref(self):
        self.assertJson(query.is_ref(query.var("x")), '{"is_ref":{"var":"x"}}')

    def test_isset(self):
        self.assertJson(query.is_set(query.var("x")), '{"is_set":{"var":"x"}}')

    def test_isdoc(self):
        self.assertJson(query.is_doc(query.var("x")), '{"is_doc":{"var":"x"}}')

    def test_islambda(self):
        self.assertJson(query.is_lambda(query.var("x")),
                        '{"is_lambda":{"var":"x"}}')

    def test_iscollection(self):
        self.assertJson(query.is_collection(query.var("x")),
                        '{"is_collection":{"var":"x"}}')

    def test_isdatabase(self):
        self.assertJson(query.is_database(query.var("x")),
                        '{"is_database":{"var":"x"}}')

    def test_isindex(self):
        self.assertJson(query.is_index(query.var("x")),
                        '{"is_index":{"var":"x"}}')

    def test_isfunction(self):
        self.assertJson(query.is_function(query.var("x")),
                        '{"is_function":{"var":"x"}}')

    def test_iskey(self):
        self.assertJson(query.is_key(query.var("x")), '{"is_key":{"var":"x"}}')

    def test_istoken(self):
        self.assertJson(query.is_token(query.var("x")),
                        '{"is_token":{"var":"x"}}')

    def test_iscredentials(self):
        self.assertJson(query.is_credentials(query.var("x")),
                        '{"is_credentials":{"var":"x"}}')

    def test_isrole(self):
        self.assertJson(query.is_role(query.var("x")),
                        '{"is_role":{"var":"x"}}')

    def test_to_string_expr(self):
        self.assertJson(query.to_string(42), '{"to_string":42}')

    def test_to_array_expr(self):
        self.assertJson(query.to_array({
            'x': 0,
            'y': 1
        }), '{"to_array":{"object":{"x":0,"y":1}}}')

    def test_to_object_expr(self):
        self.assertJson(query.to_object([['x', 0], ['y', 1]]),
                        '{"to_object":[["x",0],["y",1]]}')

    def test_to_double_expr(self):
        self.assertJson(query.to_double(42), '{"to_double":42}')

    def test_to_integer_expr(self):
        self.assertJson(query.to_integer(3.1415), '{"to_integer":3.1415}')

    def test_to_number_expr(self):
        self.assertJson(query.to_number("42"), '{"to_number":"42"}')

    def test_to_time_expr(self):
        self.assertJson(query.to_time("1970-01-01T00:00:00Z"),
                        '{"to_time":"1970-01-01T00:00:00Z"}')

    def test_to_date_expr(self):
        self.assertJson(query.to_date("1970-01-01"),
                        '{"to_date":"1970-01-01"}')

    #endregion

    def assertJson(self, obj, expected):
        self.assertEqual(to_json(obj, sort_keys=True), expected)
