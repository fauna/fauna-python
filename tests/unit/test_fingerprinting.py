from typing import Mapping
import os

import fauna


def test_fingerprinting(monkeypatch, subtests):
    tests: Mapping[str, Mapping[str, str]] = {
        "Netlify": {
            "NETLIFY_IMAGES_CDN_DOMAIN": "sup",
        },
        "Vercel": {
            "VERCEL": "sup",
        },
        "Heroku": {
            "PATH": ".heroku",
        },
        "AWS Lambda": {
            "AWS_LAMBDA_FUNCTION_VERSION": "sup"
        },
        "GCP Cloud Functions": {
            "_": "google",
        },
        "GCP Compute Instances": {
            "GOOGLE_CLOUD_PROJECT": "sup",
        },
        "Azure Cloud Functions": {
            "WEBSITE_FUNCTIONS_AZUREMONITOR_CATEGORIES": "sup"
        },
        "Azure Compute": {
            "ORYX_ENV_TYPE": "AppService",
            "WEBSITE_INSTANCE_ID": "sup",
        },
    }

    for t in tests:
        with subtests.test(t):
            # placeholder to reset PATH in case set within test (Heroku)
            current = None

            # set env vars for test
            for e in tests[t]:
                if e == "PATH":
                    current = os.environ[e]
                monkeypatch.setenv(e, tests[t][e])

            assert fauna.headers._DriverEnvironment().env == t

            # clean up
            for e in tests[t]:
                if e == "PATH" and current is not None:
                    os.environ[e] = current
                monkeypatch.delenv(e)
