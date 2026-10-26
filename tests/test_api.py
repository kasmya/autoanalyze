import io

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

CSV_CONTENT = (
    "age,income,category\n"
    "25,50000,A\n"
    "30,60000,B\n"
    "35,55000,A\n"
    "40,,B\n"
    "25,50000,A\n"
)


def _upload():
    return client.post(
        "/api/upload",
        files={"file": ("test.csv", io.BytesIO(CSV_CONTENT.encode()), "text/csv")},
    )


def test_upload_returns_analysis():
    res = _upload()
    assert res.status_code == 200
    body = res.json()
    assert body["overview"]["n_rows"] == 5
    assert body["overview"]["n_cols"] == 3
    assert "upload_id" in body
    assert len(body["summary_lines"]) > 0


def test_upload_rejects_non_csv():
    res = client.post(
        "/api/upload", files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")}
    )
    assert res.status_code == 400


def test_upload_rejects_empty_file():
    res = client.post(
        "/api/upload", files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
    )
    assert res.status_code == 400


def test_column_profile_numeric():
    upload_id = _upload().json()["upload_id"]
    res = client.get(f"/api/column/{upload_id}/age")
    assert res.status_code == 200
    body = res.json()
    assert body["is_numeric"] is True
    assert "mean" in body["stats"]
    assert body["histogram"] is not None


def test_column_profile_categorical():
    upload_id = _upload().json()["upload_id"]
    res = client.get(f"/api/column/{upload_id}/category")
    assert res.status_code == 200
    body = res.json()
    assert body["is_numeric"] is False
    assert body["top_values"] is not None


def test_column_profile_unknown_column():
    upload_id = _upload().json()["upload_id"]
    res = client.get(f"/api/column/{upload_id}/does_not_exist")
    assert res.status_code == 404


def test_column_profile_unknown_upload():
    res = client.get("/api/column/does-not-exist/age")
    assert res.status_code == 404


def test_download_cleaned_csv():
    upload_id = _upload().json()["upload_id"]
    res = client.get(f"/api/download/cleaned/{upload_id}?drop_duplicates=true")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    assert res.text.count("\n") <= 5  # original had a duplicate row


def test_download_report_html():
    upload_id = _upload().json()["upload_id"]
    res = client.get(f"/api/download/report/{upload_id}")
    assert res.status_code == 200
    assert "AutoAnalyze" in res.text
