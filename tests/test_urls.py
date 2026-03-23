import pytest

@pytest.mark.asyncio
async def test_shorten_url(client):
    response = await client.post("/api/v1/shorten", json={"url": "https://google.com"})
    assert response.status_code == 200
    data = response.json()
    assert "slug" in data
    assert "short_url" in data
    assert data["original_url"] == "https://google.com/"
    assert len(data["slug"]) == 6

@pytest.mark.asyncio
async def test_redirect(client):
    create = await client.post("/api/v1/shorten", json={"url": "https://google.com"})
    slug = create.json()["slug"]
    response = await client.get(f"/{slug}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://google.com/"

@pytest.mark.asyncio
async def test_redirect_not_found(client):
    response = await client.get("/doesnotexist", follow_redirects=False)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_custom_slug(client):
    response = await client.post("/api/v1/shorten", json={
        "url": "https://github.com",
        "custom_slug": "mygithub"
    })
    assert response.status_code == 200
    assert response.json()["slug"] == "mygithub"

@pytest.mark.asyncio
async def test_duplicate_custom_slug(client):
    await client.post("/api/v1/shorten", json={
        "url": "https://github.com",
        "custom_slug": "taken"
    })
    response = await client.post("/api/v1/shorten", json={
        "url": "https://google.com",
        "custom_slug": "taken"
    })
    assert response.status_code == 409

@pytest.mark.asyncio
async def test_invalid_url(client):
    response = await client.post("/api/v1/shorten", json={"url": "notaurl"})
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_private_network_blocked(client):
    response = await client.post("/api/v1/shorten", json={"url": "http://192.168.1.1/secret"})
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_stats(client):
    create = await client.post("/api/v1/shorten", json={"url": "https://google.com"})
    slug = create.json()["slug"]
    await client.get(f"/{slug}", follow_redirects=False)
    response = await client.get(f"/api/v1/urls/{slug}/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == slug
    assert data["total_clicks"] >= 0

@pytest.mark.asyncio
async def test_stats_not_found(client):
    response = await client.get("/api/v1/urls/doesnotexist/stats")
    assert response.status_code == 404