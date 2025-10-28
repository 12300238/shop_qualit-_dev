import json
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import uuid
from shop import *
import os

app = FastAPI(title="Shop API")

# --- In-memory repositories and services ---
users = UserRepository()
products = ProductRepository()
carts = CartRepository()
orders = OrderRepository()
invoices = InvoiceRepository()
payments = PaymentRepository()
threads = ThreadRepository()
sessions = SessionManager()
gateway = PaymentGateway()
billing = BillingService(invoices)
delivery_svc = DeliveryService()
order_svc = OrderService(orders, products, carts, payments, invoices, billing, delivery_svc, gateway, users)
auth_svc = AuthService(users, sessions)
catalog_svc = CatalogService(products)
cart_svc = CartService(carts, products)
customer_svc = CustomerService(threads, users)


# --- Chargement auto des données de test ---
def load_test_data(json_path, users_repo, products_repo, carts_repo):
    from shop import PasswordHasher, User, Product
    if not os.path.exists(json_path):
        return
    with open(json_path, 'r') as f:
        data = json.load(f)
    # Utilisateurs
    for u in data.get('users', []):
        u['password_hash'] = PasswordHasher.hash(u.pop('password'))
        user = User(**u)
        users_repo.add(user)
    # Produits
    for p in data.get('products', []):
        product = Product(**p)
        products_repo.add(product)

# Charge les données au démarrage
load_test_data(os.path.join(os.path.dirname(__file__), 'test_data.json'), users, products, carts)

# --- Models for API input/output ---
class UserIn(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    address: str
    is_admin: bool = False

class ProductIn(BaseModel):
    name: str
    description: str
    price_cents: int
    stock_qty: int
    active: Optional[bool] = True

class CartItemIn(BaseModel):
    product_id: str
    quantity: int

class OrderIn(BaseModel):
    user_id: str
    items: List[CartItemIn]

class PaymentIn(BaseModel):
    order_id: str
    card_number: str
    exp_month: int
    exp_year: int
    cvc: str

class ThreadIn(BaseModel):
    user_id: str
    subject: str
    order_id: Optional[str] = None

class MessageIn(BaseModel):
    thread_id: str
    author_user_id: Optional[str]
    body: str

# --- User endpoints ---
@app.post("/users/register")
def register_user(user: UserIn):
    """Inscription d’un nouvel utilisateur.\n
    Body: email, password, first_name, last_name, address, is_admin\n
    Retourne l’objet User créé ou erreur 400."""
    try:
        u = auth_svc.register(user.email, user.password, user.first_name, user.last_name, user.address, user.is_admin)
        return u
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/users/login")
def login_user(user: UserIn):
    """Connexion utilisateur, retourne un token de session.\n
    Body: email, password\n
    Retourne {"token": ...} ou erreur 401."""
    try:
        token = auth_svc.login(user.email, user.password)
        return {"token": token}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.delete("/users/logout")
def logout_user(token: str):
    """Déconnexion de la session utilisateur.\n
    Body: token\n
    Retourne {"ok": true}"""
    auth_svc.logout(token)
    return {"ok": True}

@app.get("/users/{user_id}")
def get_user(user_id: str):
    """Récupère les infos d’un utilisateur par son id.\n
    Retourne l’objet User ou erreur 404."""
    u = users.get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u

@app.get("/users_id/{email}")
def get_user_by_email(email: str):
    """Récupère les infos d’un utilisateur par son email.\n
    Retourne l’objet User ou erreur 404."""
    u = users.get_by_email(email)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u

# --- Product endpoints ---
@app.post("/products")
def add_product(product: ProductIn):
    """Ajoute un produit au catalogue.\n
    Body: name, description, price_cents, stock_qty, active\n
    Retourne l’objet Product créé."""
    p = Product(id=str(uuid.uuid4()), **product.dict())
    products.add(p)
    return p

@app.get("/products")
def list_products():
    """Liste tous les produits actifs du catalogue.\n
    Retourne une liste de produits."""
    return catalog_svc.list_products()

@app.get("/products/all")
def list_all_products():
    """Liste tous les produits du catalogue (admin).\n
    Retourne une liste de produits."""
    return catalog_svc.list_all_products()

@app.put("/products/{product_id}")
def update_product(product_id: str, product: ProductIn):
    """Met à jour les informations d’un produit existant (admin)."""
    existing = products.get(product_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Mise à jour simple
    existing.name = product.name
    existing.description = product.description
    existing.price_cents = product.price_cents
    existing.stock_qty = product.stock_qty
    if product.active is not None:
        existing.active = product.active if product.stock_qty > 0 else False
    else:
        existing.active = True if product.stock_qty > 0 else False
    products.add(existing)
    return existing

@app.get("/products/{product_id}")
def get_product(product_id: str):
    """Récupère un produit par son id.\n
    Retourne l’objet Product ou erreur 404."""
    p = products.get(product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return p

# --- Cart endpoints ---
@app.post("/cart/{user_id}/add")
def add_to_cart(user_id: str, item: CartItemIn):
    """Ajoute un produit au panier de l’utilisateur.\n
    Body: product_id, quantity\n
    Retourne le panier mis à jour ou erreur 400/404."""
    product = products.get(item.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    try:
        carts.get_or_create(user_id).add(product, item.quantity)
        return carts.get_or_create(user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/cart/{user_id}/remove")
def remove_from_cart(user_id: str, item: CartItemIn):
    """Retire une quantité d’un produit du panier.\n
    Body: product_id, quantity\n
    Retourne le panier mis à jour."""
    carts.get_or_create(user_id).remove(item.product_id, item.quantity)
    return carts.get_or_create(user_id)

@app.delete("/cart/{user_id}/clear")
def clear_cart(user_id: str):
    """Vide le panier de l’utilisateur.\n
    Retourne {"ok": true}"""
    carts.get_or_create(user_id).clear()
    return {"ok": True}

@app.get("/cart/{user_id}")
def view_cart(user_id: str):
    """Récupère le panier de l’utilisateur.\n
    Retourne l’objet Cart."""
    return carts.get_or_create(user_id)

@app.get("/cart/{user_id}/total")
def cart_total(user_id: str):
    """Calcule le total du panier en centimes.\n
    Retourne {"total_cents": ...}"""
    return {"total_cents": carts.get_or_create(user_id).total_cents(products)}

# --- Order endpoints ---
@app.post("/orders/checkout/{user_id}")
def checkout(user_id: str):
    """Crée une commande à partir du panier de l’utilisateur.\n
    Retourne l’objet Order ou erreur 400."""
    try:
        order = order_svc.checkout(user_id)
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/orders/{user_id}")
def view_orders(user_id: str):
    """Liste les commandes d’un utilisateur.\n
    Retourne une liste d’objets Order."""
    return order_svc.view_orders(user_id)

@app.post("/orders/pay")
def pay_by_card(payment: PaymentIn):
    """Effectue le paiement d’une commande par carte.\n
    Body: order_id, card_number, exp_month, exp_year, cvc\n
    Retourne l’objet Payment ou erreur 400."""
    try:
        pay = order_svc.pay_by_card(payment.order_id, payment.card_number, payment.exp_month, payment.exp_year, payment.cvc)
        return pay
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/orders/cancel")
def request_cancellation(user_id: str, order_id: str):
    """Demande l’annulation d’une commande.\n
    Params: user_id, order_id\n
    Retourne l’objet Order annulé ou erreur 400."""
    try:
        order = order_svc.request_cancellation(user_id, order_id)
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Backoffice endpoints ---
@app.post("/orders/validate")
def backoffice_validate_order(admin_user_id: str, order_id: str):
    """Valide une commande (admin).\n
    Params: admin_user_id, order_id\n
    Retourne l’objet Order validé ou erreur 400."""
    try:
        order = order_svc.backoffice_validate_order(admin_user_id, order_id)
        return order
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/orders/ship")
def backoffice_ship_order(admin_user_id: str, order_id: str):
    """Expédie une commande (admin).\n
    Params: admin_user_id, order_id\n
    Retourne l’objet Order expédié ou erreur 400."""
    try:
        order = order_svc.backoffice_ship_order(admin_user_id, order_id)
        return order
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/orders/mark_delivered")
def backoffice_mark_delivered(admin_user_id: str, order_id: str):
    """Marque une commande comme livrée (admin).\n
    Params: admin_user_id, order_id\n
    Retourne l’objet Order livré ou erreur 400."""
    try:
        order = order_svc.backoffice_mark_delivered(admin_user_id, order_id)
        return order
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/orders/refund")
def backoffice_refund(admin_user_id: str, order_id: str, amount_cents: Optional[int] = None):
    """Rembourse une commande (admin).\n
    Params: admin_user_id, order_id, amount_cents (optionnel)\n
    Retourne l’objet Order remboursé ou erreur 400."""
    try:
        order = order_svc.backoffice_refund(admin_user_id, order_id, amount_cents)
        return order
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Invoice endpoints ---
@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    """Récupère une facture par son id.\n
    Retourne l’objet Invoice ou erreur 404."""
    inv = invoices.get(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return inv

# --- Payment endpoints ---
@app.get("/payments/{payment_id}")
def get_payment(payment_id: str):
    """Récupère un paiement par son id.\n
    Retourne l’objet Payment ou erreur 404."""
    pay = payments.get(payment_id)
    if not pay:
        raise HTTPException(status_code=404, detail="Payment not found")
    return pay

# --- CustomerService endpoints ---
@app.post("/threads/open")
def open_thread(thread: ThreadIn):
    """Ouvre un nouveau fil de discussion (ticket support).\n
    Body: user_id, subject, order_id (optionnel)\n
    Retourne l’objet MessageThread créé."""
    th = customer_svc.open_thread(thread.user_id, thread.subject, thread.order_id)
    return th

@app.post("/threads/post")
def post_message(msg: MessageIn):
    """Ajoute un message dans un fil existant.\n
    Body: thread_id, author_user_id (optionnel), body\n
    Retourne l’objet Message ou erreur 400."""
    try:
        m = customer_svc.post_message(msg.thread_id, msg.author_user_id, msg.body)
        return m
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/threads/close")
def close_thread(thread_id: str, admin_user_id: str):
    """Ferme un fil de discussion (admin).\n
    Params: thread_id, admin_user_id\n
    Retourne l’objet MessageThread fermé ou erreur 400."""
    try:
        th = customer_svc.close_thread(thread_id, admin_user_id)
        return th
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/threads/{user_id}")
def list_threads(user_id: str):
    """Liste les fils de discussion d’un utilisateur.\n
    Retourne une liste de MessageThread."""
    return threads.list_by_user(user_id)

@app.get("/threads/messages/{thread_id}")
def get_thread_messages(thread_id: str):
    """Retourne tous les messages d’un thread spécifique."""
    thread = threads.get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread introuvable")
    return thread.messages

@app.get("/admin/threads")
def list_all_threads():
    """Liste tous les fils de discussion (tickets) — réservé aux admins."""
    return list(threads._by_id.values())

# --- Utility endpoints ---
@app.get("/status")
def status():
    """Vérifie le statut de l’API.\n
    Retourne {"status": "ok"}"""
    return {"status": "ok"}
