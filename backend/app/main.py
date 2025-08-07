"""
main.py
--------

Este módulo define la aplicación FastAPI para el backend de RepuestosApp.

Expone endpoints para:

* Verificación de salud (`GET /api/health`) para comprobar que el servicio está activo.
* Operaciones CRUD sobre productos (`GET`, `POST`, `PATCH` en `/api/productos`).
* Sincronización con Contabilium (todavía sin implementar, para que puedas ampliarlo).

El servicio usa una base de datos SQLite local (configurable vía la variable
de entorno `DB_PATH`) para persistir la información de los productos.
"""

import os
import sqlite3
from typing import List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Cargar variables de entorno desde .env (si existe).
load_dotenv()


def get_db_connection():
    """
    Obtiene una conexión SQLite usando la variable DB_PATH.
    La conexión debe cerrarse manualmente al terminar.
    """
    db_path = os.getenv("DB_PATH", "productos.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Crea las tablas necesarias si no existen:
      - repuestos: productos
      - secuencias: para generar códigos OEM secuenciales.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repuestos (
            ean TEXT PRIMARY KEY,
            oem TEXT UNIQUE,
            descripcion TEXT NOT NULL,
            precio REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            id_contabilium TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS secuencias (
            nombre TEXT PRIMARY KEY,
            ultimo_valor INTEGER
        )
    """)
    cursor.execute(
        "INSERT OR IGNORE INTO secuencias (nombre, ultimo_valor) VALUES ('oem', 0)"
    )
    conn.commit()
    conn.close()


def generate_oem(conn: sqlite3.Connection) -> str:
    """
    Incrementa la secuencia para OEM y devuelve el código de 8 dígitos con ceros a la izquierda.
    """
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE secuencias SET ultimo_valor = ultimo_valor + 1 WHERE nombre = 'oem'"
    )
    cursor.execute(
        "SELECT ultimo_valor FROM secuencias WHERE nombre = 'oem'"
    )
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("Secuencia OEM no inicializada")
    return str(row[0]).zfill(8)


class ProductCreate(BaseModel):
    descripcion: str = Field(..., description="Descripción del producto")
    precio: float = Field(..., gt=0, description="Precio del producto")
    stock: int = Field(..., ge=0, description="Cantidad en stock")
    ean: Optional[str] = Field(
        default=None, description="EAN opcional; si no se proporciona se genera"
    )


class ProductUpdate(BaseModel):
    descripcion: Optional[str] = None
    precio: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)


class ProductOut(BaseModel):
    ean: str
    oem: str
    descripcion: str
    precio: float
    stock: int
    id_contabilium: Optional[str] = None


def contabilium_headers() -> dict:
    """
    Construye las cabeceras de autorización para llamar a Contabilium.
    Devuelve un diccionario vacío si no hay API key.
    """
    apikey = os.getenv("CONTABILIUM_APIKEY")
    return {"Authorization": f"apikey {apikey}"} if apikey else {}


async def create_product_in_contabilium(product: ProductOut) -> Optional[str]:
    """
    Envía un nuevo producto a Contabilium y devuelve su ID externo.
    Es un ejemplo; ajusta la URL y el payload según la API de Contabilium.
    """
    base_url = os.getenv("CONTABILIUM_BASE_URL", "https://app.contabilium.com/api/v2")
    email = os.getenv("CONTABILIUM_EMAIL")
    api_key = os.getenv("CONTABILIUM_APIKEY")
    if not email or not api_key:
        return None
    payload = {
        "codigo": product.ean,
        "denominacion": product.descripcion,
        "precio": product.precio,
        "stock": product.stock,
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/productos",
                json=payload,
                headers=contabilium_headers(),
            )
            response.raise_for_status()
            data = response.json()
            return data.get("id")
    except Exception as exc:
        print(f"Error al crear en Contabilium: {exc}")
        return None


async def update_product_in_contabilium(ean: str, update: ProductUpdate) -> None:
    """
    Actualiza un producto en Contabilium.  
    Ajusta el endpoint y payload según la API real.
    """
    base_url = os.getenv("CONTABILIUM_BASE_URL", "https://app.contabilium.com/api/v2")
    email = os.getenv("CONTABILIUM_EMAIL")
    api_key = os.getenv("CONTABILIUM_APIKEY")
    if not email or not api_key:
        return
    payload = {}
    if update.descripcion is not None:
        payload["denominacion"] = update.descripcion
    if update.precio is not None:
        payload["precio"] = update.precio
    if update.stock is not None:
        payload["stock"] = update.stock
    try:
        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{base_url}/productos/{ean}",
                json=payload,
                headers=contabilium_headers(),
            )
    except Exception as exc:
        print(f"Error al actualizar {ean} en Contabilium: {exc}")


app = FastAPI(title="Repuestos API", version="1.0.0")

# CORS abierto para permitir que la app Ionic se comunique con el backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    """Inicializa la base de datos al arrancar la aplicación."""
    init_db()

@app.get("/api/health", tags=["Health"])
async def health() -> dict:
    """Endpoint de salud: devuelve un JSON simple."""
    return {"status": "ok"}

@app.get("/api/productos", response_model=List[ProductOut], tags=["Products"])
async def list_products() -> List[ProductOut]:
    """
    Lista todos los productos almacenados en la base local.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repuestos")
    rows = cursor.fetchall()
    conn.close()
    return [
        ProductOut(
            ean=row["ean"],
            oem=row["oem"],
            descripcion=row["descripcion"],
            precio=row["precio"],
            stock=row["stock"],
            id_contabilium=row["id_contabilium"],
        )
        for row in rows
    ]

@app.get("/api/productos/{ean}", response_model=ProductOut, tags=["Products"])
async def get_product(ean: str) -> ProductOut:
    """
    Obtiene un producto por su EAN.  
    Si no existe, devuelve 404.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repuestos WHERE ean = ?", (ean,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No existe el producto {ean}")
    return ProductOut(
        ean=row["ean"],
        oem=row["oem"],
        descripcion=row["descripcion"],
        precio=row["precio"],
        stock=row["stock"],
        id_contabilium=row["id_contabilium"],
    )

@app.post("/api/productos", response_model=ProductOut, status_code=status.HTTP_201_CREATED, tags=["Products"])
async def create_product(product: ProductCreate) -> ProductOut:
    """
    Crea un nuevo producto.  
    Si no se envía EAN, se genera un código OEM y se usa como EAN.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    # Generar EAN/OEM
    if not product.ean:
        oem_code = generate_oem(conn)
        ean = oem_code
    else:
        # Validar que no exista ese EAN
        cursor.execute("SELECT 1 FROM repuestos WHERE ean = ?", (product.ean,))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"El producto con EAN {product.ean} ya existe")
        oem_code = generate_oem(conn)
        ean = product.ean
    # Insertar
    cursor.execute(
        "INSERT INTO repuestos (ean, oem, descripcion, precio, stock) VALUES (?, ?, ?, ?, ?)",
        (ean, oem_code, product.descripcion, product.precio, product.stock)
    )
    conn.commit()
    new_product = ProductOut(
        ean=ean,
        oem=oem_code,
        descripcion=product.descripcion,
        precio=product.precio,
        stock=product.stock,
        id_contabilium=None,
    )
    # Sincronizar con Contabilium
    cont_id = await create_product_in_contabilium(new_product)
    if cont_id:
        cursor.execute("UPDATE repuestos SET id_contabilium = ? WHERE ean = ?", (cont_id, ean))
        conn.commit()
        new_product.id_contabilium = cont_id
    conn.close()
    return new_product

@app.patch("/api/productos/{ean}", response_model=ProductOut, tags=["Products"])
async def update_product(ean: str, update: ProductUpdate) -> ProductOut:
    """
    Modifica campos de un producto. Solo se actualizan campos presentes en el body.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repuestos WHERE ean = ?", (ean,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No existe el producto {ean}")
    fields = []
    values = []
    if update.descripcion is not None:
        fields.append("descripcion = ?")
        values.append(update.descripcion)
    if update.precio is not None:
        fields.append("precio = ?")
        values.append(update.precio)
    if update.stock is not None:
        fields.append("stock = ?")
        values.append(update.stock)
    values.append(ean)
    if fields:
        cursor.execute(f"UPDATE repuestos SET {', '.join(fields)} WHERE ean = ?", values)
        conn.commit()
    await update_product_in_contabilium(ean, update)
    cursor.execute("SELECT * FROM repuestos WHERE ean = ?", (ean,))
    updated_row = cursor.fetchone()
    conn.close()
    return ProductOut(
        ean=updated_row["ean"],
        oem=updated_row["oem"],
        descripcion=updated_row["descripcion"],
        precio=updated_row["precio"],
        stock=updated_row["stock"],
        id_contabilium=updated_row["id_contabilium"],
    )

@app.post("/api/sync", tags=["Sync"])
async def sync_products():
    """
    (Placeholder) Sincroniza productos con Contabilium.
    Actualmente no implementado.
    """
    return {"message": "Sync not implemented yet"}
