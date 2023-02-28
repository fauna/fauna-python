import os

import fauna


def test_fingerprinting(monkeypatch, subtests):
    with subtests.test("netlify"):
        monkeypatch.setenv("NETLIFY_IMAGES_CDN_DOMAIN", "sup")

        assert fauna.headers._DriverEnvironment().env \
            == "Netlify"
        monkeypatch.delenv("NETLIFY_IMAGES_CDN_DOMAIN")

    with subtests.test("vercel"):
        monkeypatch.setenv("VERCEL", "sup")

        assert fauna.headers._DriverEnvironment().env \
            == "Vercel"
        monkeypatch.delenv("VERCEL")

    with subtests.test("heroku"):
        path = os.environ["PATH"]
        monkeypatch.setenv("PATH", ".heroku")

        assert fauna.headers._DriverEnvironment().env \
            == "Heroku"
        monkeypatch.setenv("PATH", path)

    with subtests.test("AWS Lambda"):
        monkeypatch.setenv("AWS_LAMBDA_FUNCTION_VERSION", "sup")

        assert fauna.headers._DriverEnvironment().env \
            == "AWS Lambda"
        monkeypatch.delenv("AWS_LAMBDA_FUNCTION_VERSION")

    with subtests.test("GCP Cloud Functions"):
        monkeypatch.setenv("_", "google")

        assert fauna.headers._DriverEnvironment().env \
            == "GCP Cloud Functions"
        monkeypatch.delenv("_")

    with subtests.test("Google Compute Instances"):
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "sup")
        assert fauna.headers._DriverEnvironment().env \
            == "GCP Compute Instances"
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT")

    with subtests.test("Azure Cloud Functions"):
        monkeypatch.setenv("WEBSITE_FUNCTIONS_AZUREMONITOR_CATEGORIES", "sup")
        assert fauna.headers._DriverEnvironment().env \
            == "Azure Cloud Functions"
        monkeypatch.delenv("WEBSITE_FUNCTIONS_AZUREMONITOR_CATEGORIES")

    with subtests.test("Azure Compute"):
        monkeypatch.setenv("ORYX_ENV_TYPE", "sup")
        monkeypatch.setenv("WEBSITE_INSTANCE_ID", "sup")
        monkeypatch.setenv("ORYX_ENV_TYPE", "AppService")

        assert fauna.headers._DriverEnvironment().env \
            == "Azure Compute"

        monkeypatch.delenv("ORYX_ENV_TYPE")
        monkeypatch.delenv("WEBSITE_INSTANCE_ID")
        monkeypatch.delenv("ORYX_ENV_TYPE", False)
