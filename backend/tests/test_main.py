from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    """Test health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_create_and_get_product():
    """Test product creation and retrieval."""
    prod = {"id": "123", "name": "Filtro", "stock": 5}
    response = client.post("/api/productos", json=prod)
    assert response.status_code == 201
    response = client.get("/api/productos/123")
    assert response.status_code == 200
    assert response.json()["name"] == "Filtro"

def test_get_nonexistent():
    """Test 404 for missing product."""
    response = client.get("/api/productos/00000000")
    assert response.status_code == 404

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    """Test health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_get_product():
    """Test product creation and retrieval."""
    prod = {"id": "123", "name": "Filtro", "stock": 5}
    response = client.post("/api/productos", json=prod)
    assert response.status_code == 201
    response = client.get("/api/productos/123")
    assert response.status_code == 200
    assert response.json()["name"] == "Filtro"

def test_get_nonexistent():
    """Test 404 for missing product."""
    response = client.get("/api/productos/00000000")
    assert response.status_code == 404
