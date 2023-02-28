import fauna

# IMPORTANT: Not using subtests to avoid env var issues


def test_netlify(monkeypatch):
    monkeypatch.setenv("NETLIFY_IMAGES_CDN_DOMAIN", "sup")

    assert fauna.headers._DriverEnvironment().env \
        == "Netlify"


def test_vercel(monkeypatch):
    monkeypatch.setenv("VERCEL", "sup")

    assert fauna.headers._DriverEnvironment().env \
        == "Vercel"


def test_heroku(monkeypatch):
    monkeypatch.setenv("PATH", ".heroku")

    assert fauna.headers._DriverEnvironment().env \
        == "Heroku"


def test_lambda(monkeypatch):
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_VERSION", "sup")

    assert fauna.headers._DriverEnvironment().env \
        == "AWS Lambda"


def test_gcp_cloud_functions(monkeypatch):
    monkeypatch.setenv("_", "google")

    assert fauna.headers._DriverEnvironment().env \
        == "GCP Cloud Functions"


def test_gcp_compute_instances(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "sup")
    assert fauna.headers._DriverEnvironment().env \
        == "GCP Compute Instances"


def test_azure_cloud_functions(monkeypatch):
    monkeypatch.setenv("WEBSITE_FUNCTIONS_AZUREMONITOR_CATEGORIES", "sup")
    assert fauna.headers._DriverEnvironment().env \
        == "Azure Cloud Functions"


def test_azure_compute(monkeypatch):
    monkeypatch.setenv("ORYX_ENV_TYPE", "sup")
    monkeypatch.setenv("WEBSITE_INSTANCE_ID", "sup")
    monkeypatch.setenv("ORYX_ENV_TYPE", "AppService")

    assert fauna.headers._DriverEnvironment().env \
        == "Azure Compute"
