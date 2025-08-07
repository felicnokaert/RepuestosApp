
# main.py: FastAPI app with SQLite, Contabilium sync, and product CRUD endpoints

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import os
import requests

# --- Environment Variables ---
CONTABILIUM_API_KEY = os.getenv("CONTABILIUM_API_KEY", "dummy-key")
CONTABILIUM_API_URL = os.getenv("CONTABILIUM_API_URL", "https://api.contabilium.com/api/v1/products")
DATABASE_URL = os.getenv("DATABASE_URL", "products.db")

# --- Database Utilities ---
def get_db():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with sqlite3.connect(DATABASE_URL) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            stock INTEGER DEFAULT 0
        )
        """)
init_db()

# --- Pydantic Schemas ---
class Product(BaseModel):
    id: str
    name: str
    stock: int

class ProductCreate(BaseModel):
    id: str
    name: str
    stock: Optional[int] = 0

# --- FastAPI App ---
app = FastAPI(
    title="RepuestosApp API",
    description="API para gestión de repuestos y sincronización con Contabilium",
    version="1.0.0"
)

# --- CORS (for local frontend dev) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Health Check Endpoint ---
@app.get("/api/health")
def health():
    """Simple health check endpoint."""
    return {"status": "ok"}

# --- CRUD Endpoints ---
@app.get("/api/productos", response_model=List[Product])
def list_products(db=Depends(get_db)):
    """List all products."""
    cur = db.execute("SELECT * FROM products")
    return [dict(row) for row in cur.fetchall()]

@app.get("/api/productos/{product_id}", response_model=Product)
def get_product(product_id: str, db=Depends(get_db)):
    """Get a product by ID."""
    cur = db.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    return dict(row)

@app.post("/api/productos", response_model=Product, status_code=201)
def create_product(product: ProductCreate, db=Depends(get_db)):
    """Create a new product."""
    try:
        db.execute("INSERT INTO products (id, name, stock) VALUES (?, ?, ?)",
                   (product.id, product.name, product.stock))
        db.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Product ID already exists")
    return product

@app.put("/api/productos/{product_id}", response_model=Product)
def update_product(product_id: str, product: ProductCreate, db=Depends(get_db)):
    """Update an existing product."""
    cur = db.execute("UPDATE products SET name=?, stock=? WHERE id=?",
                     (product.name, product.stock, product_id))
    db.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.delete("/api/productos/{product_id}", status_code=204)
def delete_product(product_id: str, db=Depends(get_db)):
    """Delete a product."""
    cur = db.execute("DELETE FROM products WHERE id=?", (product_id,))
    db.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Product not found")

# --- Contabilium Sync Endpoint ---
@app.post("/api/sync")
def sync_with_contabilium(db=Depends(get_db)):
    """Sync local products with Contabilium API."""
    headers = {"Authorization": f"Bearer {CONTABILIUM_API_KEY}"}
    cur = db.execute("SELECT * FROM products")
    products = [dict(row) for row in cur.fetchall()]
    # Example: send all products to Contabilium (adjust as needed)
    try:
        resp = requests.post(CONTABILIUM_API_URL, json=products, headers=headers, timeout=10)
        resp.raise_for_status()
        return {"status": "synced", "contabilium_response": resp.json()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")