from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional
import uuid
import time


# ==========================================================
# 🧑‍💼 GESTION UTILISATEURS
# ==========================================================

@dataclass
class User:
    """Représente un utilisateur du système.

    Attributs principaux:
        id, email, password_hash, first_name, last_name, address, is_admin
    """
    id: str
    email: str
    password_hash: str
    first_name: str
    last_name: str
    address: str
    is_admin: bool = False


    def update_profile(self, **fields):
        """Met à jour les champs modifiables du profil.

        Ne permet pas de modifier: id, email, is_admin, password_hash.

        Args:
            **fields: paires nom=valeur des attributs à mettre à jour.
        """
        for k, v in fields.items():
            if hasattr(self, k) and k not in {"id", "email", "is_admin", "password_hash"}:
                setattr(self, k, v)

class UserRepository:
    """Repository en mémoire pour les objets `User`.

    Indexe par id et par email (insensible à la casse).
    """
    def __init__(self):
        self._by_id: Dict[str, User] = {}
        self._by_email: Dict[str, User] = {}

    def add(self, user: User):
        """Ajoute ou remplace un utilisateur dans le repository."""
        self._by_id[user.id] = user
        self._by_email[user.email.lower()] = user

    def get(self, user_id: str) -> Optional[User]:
        """Retourne l'utilisateur par identifiant ou None si introuvable."""
        return self._by_id.get(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        """Retourne l'utilisateur par email (insensible à la casse)."""
        return self._by_email.get(email.lower())
    
class PasswordHasher:
    """Outils de hachage/verification de mot de passe.
    """
    @staticmethod
    def hash(password: str) -> str:
        return f"sha256::{hash(password)}"

    @staticmethod
    def verify(password: str, stored_hash: str) -> bool:
        """Vérifie si le mot de passe correspond au haché stocké."""
        return PasswordHasher.hash(password) == stored_hash
    
class SessionManager:
    """Gestion simple de sessions en mémoire.

    Stocke un mapping token -> user_id.
    """
    def __init__(self):
        self._sessions: Dict[str, str] = {}

    def create_session(self, user_id: str) -> str:
        """Crée une session pour l'utilisateur et retourne le token."""
        token = str(uuid.uuid4())
        self._sessions[token] = user_id
        return token

    def destroy_session(self, token: str):
        """Détruit la session associée au token (si existe)."""
        self._sessions.pop(token, None)

    def get_user_id(self, token: str) -> Optional[str]:
        """Retourne l'user_id associé au token ou None."""
        return self._sessions.get(token)

class AuthService:
    """Service d'authentification: inscription/login/logout.

    Utilise `UserRepository` et `SessionManager`.
    """
    def __init__(self, users: UserRepository, sessions: SessionManager):
        self.users = users
        self.sessions = sessions

    def register(self, email: str, password: str, first_name: str, last_name: str, address: str, is_admin: bool=False) -> User:
        """Enregistre un nouvel utilisateur et retourne l'objet `User`.

        Lève ValueError si l'email est déjà utilisé.
        """
        if self.users.get_by_email(email):
            raise ValueError("Email déjà utilisé.")
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            password_hash=PasswordHasher.hash(password),
            first_name=first_name,
            last_name=last_name,
            address=address,
            is_admin=is_admin
        )
        self.users.add(user)
        return user

    def login(self, email: str, password: str) -> str:
        """Vérifie les identifiants et crée une session. Retourne le token."""
        user = self.users.get_by_email(email)
        if not user or not PasswordHasher.verify(password, user.password_hash):
            raise ValueError("Identifiants invalides.")
        return self.sessions.create_session(user.id)

    def logout(self, token: str):
        """Déconnecte la session identifiée par le token."""
        self.sessions.destroy_session(token)


# ==========================================================
# 🛒 CATALOGUE & PANIER
# ==========================================================

@dataclass
class Product:
    """Représente un produit du catalogue.

    Attributs: id, name, description, price_cents, stock_qty, active
    """
    id: str
    name: str
    description: str
    price_cents: int
    stock_qty: int
    active: bool = True

class ProductRepository:
    """Repository en mémoire des produits disponibles."""
    def __init__(self):
        self._by_id: Dict[str, Product] = {}

    def add(self, product: Product):
        """Ajoute ou met à jour un produit."""
        self._by_id[product.id] = product

    def get(self, product_id: str) -> Optional[Product]:
        """Retourne le produit par identifiant ou None."""
        return self._by_id.get(product_id)

    def list_active(self) -> List[Product]:
        """Liste tous les produits actifs."""
        return [p for p in self._by_id.values() if p.active]
    
    def list_all(self) -> List[Product]:
        """Liste tous les produits, actifs ou non."""
        return list(self._by_id.values())

    def reserve_stock(self, product_id: str, qty: int):
        """Réserve (débite) `qty` unités du stock d'un produit.

        Lève ValueError si produit introuvable ou stock insuffisant.
        """
        p = self.get(product_id)
        if not p or p.stock_qty < qty:
            raise ValueError("Stock insuffisant.")
        p.stock_qty -= qty

    def release_stock(self, product_id: str, qty: int):
        """Remet `qty` unités en stock pour le produit donné (si trouvé)."""
        p = self.get(product_id)
        if p:
            p.stock_qty += qty

@dataclass
class CartItem:
    """Element simple d'un panier: référence produit + quantité."""
    product_id: str
    quantity: int

@dataclass
class Cart:
    """Panier utilisateur en mémoire.

    Fournit ajout/suppression/vidage et calcul du total en centimes.
    """
    user_id: str
    items: Dict[str, CartItem] = field(default_factory=dict)


    def add(self, product: Product, qty: int = 1):
        """Ajoute une quantité donnée d'un produit au panier.

        Args:
            product: instance de `Product` à ajouter.
            qty: quantité à ajouter (doit être > 0).
        Raises:
            ValueError: en cas de quantité invalide, produit inactif ou stock insuffisant.
        """
        if qty <= 0:
            raise ValueError("Quantité invalide.")
        if not product.active:
            raise ValueError("Produit inactif.")
        if product.stock_qty < qty:
            raise ValueError("Stock insuffisant.")
        if product.id in self.items:
            self.items[product.id].quantity += qty
        else:
            self.items[product.id] = CartItem(product_id=product.id, quantity=qty)


    def remove(self, product_id: str, qty: int = 1):
        """Supprime une quantité d'un produit du panier.

        Si qty <= 0 supprime entièrement l'entrée.
        """
        if product_id not in self.items:
            return
        if qty <= 0:
            del self.items[product_id]
            return
        self.items[product_id].quantity -= qty
        if self.items[product_id].quantity <= 0:
            del self.items[product_id]


    def clear(self):
        """Vide le panier."""
        self.items.clear()


    def total_cents(self, product_repo: "ProductRepository") -> int:
        """Calcule le total du panier en centimes en interrogeant `product_repo`.

        Retourne 0 pour les produits introuvables ou inactifs.
        """
        total = 0
        for it in self.items.values():
            p = product_repo.get(it.product_id)
            if p is None or not p.active:
                continue
            total += p.price_cents * it.quantity
        return total
    
class CartRepository:
    """Repository en mémoire pour les paniers utilisateurs."""
    def __init__(self):
        self._by_user: Dict[str, Cart] = {}

    def get_or_create(self, user_id: str) -> Cart:
        """Retourne le panier de l'utilisateur, en crée un si nécessaire."""
        if user_id not in self._by_user:
            self._by_user[user_id] = Cart(user_id=user_id)
        return self._by_user[user_id]

    def clear(self, user_id: str):
        """Vide le panier de l'utilisateur donné."""
        self.get_or_create(user_id).clear()

class CatalogService:
    """Service simple pour exposer le catalogue de produits."""
    def __init__(self, products: ProductRepository):
        self.products = products

    def list_products(self) -> List[Product]:
        """Retourne la liste des produits actifs."""
        return self.products.list_active()
    
    def list_all_products(self) -> List[Product]:
        """Retourne la liste de tous les produits, actifs ou non."""
        return self.products.list_all()
    
class CartService:
    """Service de gestion du panier côté application/logique métier."""
    def __init__(self, carts: CartRepository, products: ProductRepository):
        self.carts = carts
        self.products = products

    def add_to_cart(self, user_id: str, product_id: str, qty: int = 1):
        """Ajoute `qty` du produit au panier de l'utilisateur."""
        product = self.products.get(product_id)
        if not product:
            raise ValueError("Produit introuvable.")
        self.carts.get_or_create(user_id).add(product, qty)

    def remove_from_cart(self, user_id: str, product_id: str, qty: int = 1):
        """Retire `qty` du produit du panier de l'utilisateur."""
        self.carts.get_or_create(user_id).remove(product_id, qty)

    def view_cart(self, user_id: str) -> Cart:
        """Retourne l'objet `Cart` de l'utilisateur."""
        return self.carts.get_or_create(user_id)

    def cart_total(self, user_id: str) -> int:
        """Calcule le total du panier (en centimes)."""
        return self.carts.get_or_create(user_id).total_cents(self.products)
    
# ==========================================================
# 📦 COMMANDES / PAIEMENTS / LIVRAISON / FACTURATION
# ==========================================================

class OrderStatus(Enum):
    """Enum représentant les différents statuts possibles d'une commande.

    Valeurs:
        CREE, VALIDEE, PAYEE, EXPEDIEE, LIVREE, ANNULEE, REMBOURSEE
    """
    CREE = auto()
    VALIDEE = auto()
    PAYEE = auto()
    EXPEDIEE = auto()
    LIVREE = auto()
    ANNULEE = auto()
    REMBOURSEE = auto()

@dataclass
class OrderItem:
    """Item inclus dans une commande (copie des données produit au moment de la commande)."""
    product_id: str
    name: str
    unit_price_cents: int
    quantity: int

@dataclass
class Order:
    """Représente une commande client avec ses métadonnées et statuts.

    Attributs importants: items (List[OrderItem]), status (OrderStatus), timestamps
    """
    id: str
    user_id: str
    items: List[OrderItem]
    status: OrderStatus
    created_at: float
    validated_at: Optional[float] = None
    paid_at: Optional[float] = None
    shipped_at: Optional[float] = None
    delivered_at: Optional[float] = None
    cancelled_at: Optional[float] = None
    refunded_at: Optional[float] = None
    delivery: Optional[Delivery] = None
    invoice_id: Optional[str] = None
    payment_id: Optional[str] = None


    def total_cents(self) -> int:
        return sum(i.unit_price_cents * i.quantity for i in self.items)
    
class OrderRepository:
    """Repository en mémoire pour les commandes."""
    def __init__(self):
        self._by_id: Dict[str, Order] = {}
        self._by_user: Dict[str, List[str]] = {}

    def add(self, order: Order):
        """Ajoute une commande et indexe par utilisateur."""
        self._by_id[order.id] = order
        self._by_user.setdefault(order.user_id, []).append(order.id)

    def get(self, order_id: str) -> Optional[Order]:
        """Retourne la commande par identifiant ou None."""
        return self._by_id.get(order_id)

    def list_by_user(self, user_id: str) -> List[Order]:
        """Liste les commandes d'un utilisateur (ordre d'ajout)."""
        return [self._by_id[oid] for oid in self._by_user.get(user_id, [])]

    def update(self, order: Order):
        """Met à jour une commande existante (ou la remplace)."""
        self._by_id[order.id] = order

@dataclass
class InvoiceLine:
    """Ligne de facture: description d'un item facturé."""
    product_id: str
    name: str
    unit_price_cents: int
    quantity: int
    line_total_cents: int

@dataclass
class Invoice:
    """Document de facturation lié à une commande.

    Contient les lignes de facturation et le montant total en centimes.
    """
    id: str
    order_id: str
    user_id: str
    lines: List[InvoiceLine]
    total_cents: int
    issued_at: float

class InvoiceRepository:
    """Repository en mémoire pour les factures."""
    def __init__(self):
        self._by_id: Dict[str, Invoice] = {}

    def add(self, invoice: Invoice):
        """Ajoute une facture."""
        self._by_id[invoice.id] = invoice

    def get(self, invoice_id: str) -> Optional[Invoice]:
        """Retourne la facture par identifiant ou None."""
        return self._by_id.get(invoice_id)
    
@dataclass
class Payment:
    """Enregistrement d'un paiement effectué pour une commande."""
    id: str
    order_id: str
    user_id: str
    amount_cents: int
    provider: str
    provider_ref: Optional[str]
    succeeded: bool
    created_at: float

class PaymentRepository:
    """Repository en mémoire pour les paiements."""
    def __init__(self):
        self._by_id: Dict[str, Payment] = {}

    def add(self, payment: Payment):
        """Ajoute un paiement au repository."""
        self._by_id[payment.id] = payment

    def get(self, payment_id: str) -> Optional[Payment]:
        """Retourne le paiement par identifiant ou None."""
        return self._by_id.get(payment_id)
    
@dataclass
class Delivery:
    """Informations sur une expédition (transporteur, tracking, adresse, statut)."""
    id: str
    order_id: str
    carrier: str
    tracking_number: Optional[str]
    address: str
    status: str

class BillingService:
    """Service responsable de la création et stockage des factures."""
    def __init__(self, invoices: InvoiceRepository):
        self.invoices = invoices

    def issue_invoice(self, order: Order) -> Invoice:
        """Génère une `Invoice` pour la commande donnée et l'enregistre.

        Args:
            order: commande source
        Returns:
            Invoice créée et ajoutée au repository.
        """
        lines = [
            InvoiceLine(
                product_id=i.product_id,
                name=i.name,
                unit_price_cents=i.unit_price_cents,
                quantity=i.quantity,
                line_total_cents=i.unit_price_cents * i.quantity
            )
            for i in order.items
        ]
        inv = Invoice(
            id=str(uuid.uuid4()),
            order_id=order.id,
            user_id=order.user_id,
            lines=lines,
            total_cents=sum(l.line_total_cents for l in lines),
            issued_at=time.time()
        )
        self.invoices.add(inv)
        return inv
    
class PaymentGateway:
    """Simulation d'un prestataire de paiement (mock).

    Méthodes:
        charge_card(...): tente de débiter une carte (mock)
        refund(...): simule un remboursement
    """
    def charge_card(self, card_number: str, exp_month: int, exp_year: int, cvc: str, amount_cents: int, idempotency_key: str) -> Dict:
        """Tente de débiter la carte et retourne un dict résultat.

        La simulation renvoie success=False si le numéro finit par '0000'.
        """
        ok = not card_number.endswith("0000")
        return {
            "success": ok,
            "transaction_id": str(uuid.uuid4()) if ok else None,
            "failure_reason": None if ok else "CARTE_REFUSEE"
        }

    def refund(self, transaction_id: str, amount_cents: int) -> Dict:
        """Simule un remboursement et retourne les métadonnées du refund."""
        return {
            "success": True,
            "refund_id": str(uuid.uuid4())
        }
    
class DeliveryService:
    """Service minimal pour préparer/expédier/marquer comme livré une livraison."""
    def prepare_delivery(self, order: Order, address: str, carrier: str = "POSTE") -> Delivery:
        """Prépare une instance `Delivery` pour une commande (statut PREPAREE)."""
        delivery = Delivery(
            id=str(uuid.uuid4()),
            order_id=order.id,
            carrier=carrier,
            tracking_number=None,
            address=address,
            status="PREPAREE"
        )
        return delivery

    def ship(self, delivery: Delivery) -> Delivery:
        """Marque la livraison comme en cours et génère un tracking si absent."""
        delivery.status = "EN_COURS"
        delivery.tracking_number = delivery.tracking_number or f"TRK-{uuid.uuid4().hex[:10].upper()}"
        return delivery

    def mark_delivered(self, delivery: Delivery) -> Delivery:
        """Marque la livraison comme livrée."""
        delivery.status = "LIVREE"
        return delivery
    
class OrderService:
    """Service principal d'orchestration des commandes (checkout, paiement, backoffice)."""
    def __init__(
        self,
        orders: OrderRepository,
        products: ProductRepository,
        carts: CartRepository,
        payments: PaymentRepository,
        invoices: InvoiceRepository,
        billing: BillingService,
        delivery_svc: DeliveryService,
        gateway: PaymentGateway,
        users: UserRepository
    ):
        self.orders = orders
        self.products = products
        self.carts = carts
        self.payments = payments
        self.invoices = invoices
        self.billing = billing
        self.delivery_svc = delivery_svc
        self.gateway = gateway
        self.users = users

    def checkout(self, user_id: str) -> Order:
        """Crée une commande à partir du panier de l'utilisateur.

        Réserve le stock et vide le panier.
        """
        cart = self.carts.get_or_create(user_id)
        if not cart.items:
            raise ValueError("Panier vide.")
        order_items: List[OrderItem] = []
        for it in cart.items.values():
            p = self.products.get(it.product_id)
            if not p or not p.active:
                raise ValueError("Produit indisponible.")
            if p.stock_qty < it.quantity:
                raise ValueError(f"Stock insuffisant pour {p.name}.")
            self.products.reserve_stock(p.id, it.quantity)
            if p.stock_qty <= 0:
                p.active = False
            order_items.append(OrderItem(
                product_id=p.id,
                name=p.name,
                unit_price_cents=p.price_cents,
                quantity=it.quantity
            ))
        order = Order(
            id=str(uuid.uuid4()),
            user_id=user_id,
            items=order_items,
            status=OrderStatus.CREE,
            created_at=time.time()
        )
        self.orders.add(order)
        self.carts.clear(user_id)
        return order

    def pay_by_card(self, order_id: str, card_number: str, exp_month: int, exp_year: int, cvc: str) -> Payment:
        """Effectue un paiement par carte pour la commande donnée.

        Utilise `PaymentGateway` et met à jour l'état de la commande.
        """
        order = self.orders.get(order_id)
        if not order:
            raise ValueError("Commande introuvable.")
        if order.status not in {OrderStatus.CREE, OrderStatus.VALIDEE}:
            raise ValueError("Statut de commande incompatible avec le paiement.")
        amount = order.total_cents()
        res = self.gateway.charge_card(
            card_number, exp_month, exp_year, cvc, amount, idempotency_key=order.id
        )
        payment = Payment(
            id=str(uuid.uuid4()),
            order_id=order.id,
            user_id=order.user_id,
            amount_cents=amount,
            provider="CB",
            provider_ref=res.get("transaction_id"),
            succeeded=res["success"],
            created_at=time.time()
        )
        self.payments.add(payment)
        if not payment.succeeded:
            raise ValueError("Paiement refusé.")
        order.payment_id = payment.id
        order.status = OrderStatus.PAYEE
        order.paid_at = time.time()
        inv = self.billing.issue_invoice(order)
        order.invoice_id = inv.id
        self.orders.update(order)
        return payment

    def view_orders(self, user_id: str) -> List[Order]:
        """Retourne la liste des commandes d'un utilisateur."""
        return self.orders.list_by_user(user_id)

    def request_cancellation(self, user_id: str, order_id: str) -> Order:
        """Demande d'annulation par l'utilisateur; restitue le stock si OK."""
        order = self.orders.get(order_id)
        if not order or order.user_id != user_id:
            raise ValueError("Commande introuvable.")
        if order.status in {OrderStatus.EXPEDIEE, OrderStatus.LIVREE}:
            raise ValueError("Trop tard pour annuler : commande expédiée.")
        order.status = OrderStatus.ANNULEE
        order.cancelled_at = time.time()
        for it in order.items:
            self.products.release_stock(it.product_id, it.quantity)
        self.orders.update(order)
        return order

    def backoffice_validate_order(self, admin_user_id: str, order_id: str) -> Order:
        """Validation manuelle d'une commande par un administrateur."""
        admin = self.users.get(admin_user_id)
        if not admin or not admin.is_admin:
            raise PermissionError("Droits insuffisants.")
        order = self.orders.get(order_id)
        if not order or order.status != OrderStatus.CREE:
            raise ValueError("Commande introuvable ou mauvais statut.")
        order.status = OrderStatus.VALIDEE
        order.validated_at = time.time()
        self.orders.update(order)
        return order

    def backoffice_ship_order(self, admin_user_id: str, order_id: str) -> Order:
        """Prépare et marque la commande comme expédiée (backoffice)."""
        admin = self.users.get(admin_user_id)
        if not admin or not admin.is_admin:
            raise PermissionError("Droits insuffisants.")
        order = self.orders.get(order_id)
        if not order or order.status != OrderStatus.PAYEE:
            raise ValueError("La commande doit être payée pour être expédiée.")
        user = self.users.get(order.user_id)
        if not user:
            raise ValueError("Utilisateur lié à la commande introuvable.")
        delivery = self.delivery_svc.prepare_delivery(order, address=user.address)
        delivery = self.delivery_svc.ship(delivery)
        order.delivery = delivery
        order.status = OrderStatus.EXPEDIEE
        order.shipped_at = time.time()
        self.orders.update(order)
        return order

    def backoffice_mark_delivered(self, admin_user_id: str, order_id: str) -> Order:
        """Marque une commande comme livrée (backoffice)."""
        admin = self.users.get(admin_user_id)
        if not admin or not admin.is_admin:
            raise PermissionError("Droits insuffisants.")
        order = self.orders.get(order_id)
        if not order or order.status != OrderStatus.EXPEDIEE or not order.delivery:
            raise ValueError("Commande non expédiée.")
        self.delivery_svc.mark_delivered(order.delivery)
        order.status = OrderStatus.LIVREE
        order.delivered_at = time.time()
        self.orders.update(order)
        return order

    def backoffice_refund(self, admin_user_id: str, order_id: str, amount_cents: Optional[int] = None) -> Order:
        """Effectue un remboursement (total ou partiel) via le PSP mock."""
        admin = self.users.get(admin_user_id)
        if not admin or not admin.is_admin:
            raise PermissionError("Droits insuffisants.")
        order = self.orders.get(order_id)
        if not order or order.status not in {OrderStatus.PAYEE, OrderStatus.ANNULEE}:
            raise ValueError("Remboursement non autorisé au statut actuel.")
        amount = amount_cents or order.total_cents()
        payment = self.payments.get(order.payment_id) if order.payment_id else None
        if not payment or not payment.provider_ref:
            raise ValueError("Aucun paiement initial.")
        self.gateway.refund(payment.provider_ref, amount)
        order.status = OrderStatus.REMBOURSEE
        order.refunded_at = time.time()
        for it in order.items:
            self.products.release_stock(it.product_id, it.quantity)
        self.orders.update(order)
        return order
    
# ==========================================================
# 🎫 SUPPORT CLIENT / TICKETS
# ==========================================================

@dataclass
class MessageThread:
    """Fil de discussion support/utilisateur lié optionnellement à une commande."""
    id: str
    user_id: str
    order_id: Optional[str]
    subject: str
    messages: List["Message"] = field(default_factory=list)
    closed: bool = False
    created_at: float = field(default_factory=time.time)

@dataclass
class Message:
    """Message individuel dans un `MessageThread`."""
    id: str
    thread_id: str
    author_user_id: Optional[str]
    body: str
    created_at: float

class ThreadRepository:
    """Repository des fils de discussion / tickets de support."""
    def __init__(self):
        self._by_id: Dict[str, MessageThread] = {}

    def add(self, thread: MessageThread):
        """Ajoute un fil de discussion."""
        self._by_id[thread.id] = thread

    def get(self, thread_id: str) -> Optional[MessageThread]:
        """Récupère un fil par identifiant."""
        return self._by_id.get(thread_id)

    def list_by_user(self, user_id: str) -> List[MessageThread]:
        """Liste les fils appartenant à un utilisateur."""
        return [t for t in self._by_id.values() if t.user_id == user_id]
    
class CustomerService:
    """Service support client: gestion des fils de discussion et messages."""
    def __init__(self, threads: ThreadRepository, users: UserRepository):
        self.threads = threads
        self.users = users

    def open_thread(self, user_id: str, subject: str, order_id: Optional[str] = None) -> MessageThread:
        """Ouvre un nouveau fil de discussion (ticket) pour l'utilisateur."""
        th = MessageThread(id=str(uuid.uuid4()), user_id=user_id, order_id=order_id, subject=subject)
        self.threads.add(th)
        return th

    def post_message(self, thread_id: str, author_user_id: Optional[str], body: str) -> Message:
        """Ajoute un message dans un fil existant. author_user_id=None pour agent."""
        th = self.threads.get(thread_id)
        if not th or th.closed:
            raise ValueError("Fil introuvable ou fermé.")
        if author_user_id is not None and not self.users.get(author_user_id):
            raise ValueError("Auteur inconnu.")
        msg = Message(id=str(uuid.uuid4()), thread_id=thread_id, author_user_id=author_user_id, body=body, created_at=time.time())
        th.messages.append(msg)
        return msg

    def close_thread(self, thread_id: str, admin_user_id: str):
        """Ferme un fil (action réservée aux admins/support)."""
        admin = self.users.get(admin_user_id)
        if not admin or not admin.is_admin:
            raise PermissionError("Droits insuffisants.")
        th = self.threads.get(thread_id)
        if not th:
            raise ValueError("Fil introuvable.")
        th.closed = True
        return th