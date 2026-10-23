from tests.factories import TEST_PASSWORD


def test_login_returns_token_and_user(client, seeded):
    r = client.post("/auth/login", json={"email": "admin@acme.example", "password": TEST_PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["token"]
    assert body["user"]["email"] == "admin@acme.example"
    assert body["user"]["role"] == "hr_admin"


def test_login_is_case_insensitive_on_email(client, seeded):
    r = client.post("/auth/login", json={"email": "ADMIN@acme.example", "password": TEST_PASSWORD})
    assert r.status_code == 200


def test_login_wrong_password(client, seeded):
    r = client.post("/auth/login", json={"email": "admin@acme.example", "password": "nope"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid email or password"


def test_login_unknown_email_gives_same_error(client, seeded):
    r = client.post("/auth/login", json={"email": "ghost@acme.example", "password": "nope"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid email or password"


def test_login_rejects_malformed_email(client, seeded):
    r = client.post("/auth/login", json={"email": "not-an-email", "password": "x"})
    assert r.status_code == 422


def test_me_requires_token(client, seeded):
    r = client.get("/auth/me")
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"] == "Bearer"


def test_me_rejects_garbage_token(client, seeded):
    r = client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401


def test_me_returns_current_user(client, admin_headers):
    r = client.get("/auth/me", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["role"] == "hr_admin"


def test_viewer_token_resolves_viewer_role(client, viewer_headers):
    r = client.get("/auth/me", headers=viewer_headers)
    assert r.json()["role"] == "hr_viewer"
