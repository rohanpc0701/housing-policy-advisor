"""BLS API response parsing."""

from unittest.mock import patch

from housing_policy_advisor.data.clients import bls_client


def test_bls_accepts_lowercase_results_key():
    payload = {
        "status": "REQUEST_SUCCEEDED",
        "message": [],
        "results": {
            "series": [
                {
                    "seriesID": "LAUCN51121000000003",
                    "data": [{"year": "2024", "period": "M01", "latest": "true", "value": "3.2"}],
                }
            ]
        },
    }

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return payload

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, url, json=None, timeout=None):
            return FakeResp()

    with patch.object(bls_client.httpx, "Client", lambda *a, **k: FakeClient()):
        out = bls_client.fetch_laus_county_data("51", "121", api_key="x")
    assert out.get("unemployment_rate") == 0.032
