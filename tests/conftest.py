import pytest

@pytest.fixture(autouse=True)
def isolated_runtime(monkeypatch,tmp_path):
    import backend.main as service
    monkeypatch.setattr(service,'RUNTIME',tmp_path/'runtime')
    monkeypatch.delenv('AUTH_COOKIE_NAME',raising=False)
