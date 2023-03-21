from typing import Mapping

from fauna.client.headers import _DriverEnvironment


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
        with monkeypatch.context() as m:
            with subtests.test(t):
                for e in tests[t]:
                    m.setenv(e, tests[t][e])

                assert _DriverEnvironment().env == t
