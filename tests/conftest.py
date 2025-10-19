import pytest
import time
import uuid
import os
import sys
from typing import Generator

# Ensure project root is on sys.path so tests can import `shop` even when pytest
# is run from outside the virtualenv or with a different working directory.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from shop import (
    UserRepository, ProductRepository, CartRepository, OrderRepository,
    InvoiceRepository, PaymentRepository, ThreadRepository,
    SessionManager, AuthService, CatalogService, CartService,
    BillingService, DeliveryService, PaymentGateway, OrderService,
    CustomerService, User, Product
)


@pytest.fixture
def users():
    return UserRepository()


@pytest.fixture
def products():
    return ProductRepository()


@pytest.fixture
def carts():
    return CartRepository()


@pytest.fixture
def orders():
    return OrderRepository()


@pytest.fixture
def invoices():
    return InvoiceRepository()


@pytest.fixture
def payments():
    return PaymentRepository()


@pytest.fixture
def threads():
    return ThreadRepository()


@pytest.fixture
def sessions():
    return SessionManager()


@pytest.fixture
def services(users, products, carts, orders, invoices, payments, threads, sessions):
    auth = AuthService(users, sessions)
    catalog = CatalogService(products)
    cart_svc = CartService(carts, products)
    billing = BillingService(invoices)
    delivery_svc = DeliveryService()
    gateway = PaymentGateway()
    order_svc = OrderService(orders, products, carts, payments, invoices, billing, delivery_svc, gateway, users)
    cs = CustomerService(threads, users)
    return {
        'auth': auth,
        'catalog': catalog,
        'cart_svc': cart_svc,
        'billing': billing,
        'delivery_svc': delivery_svc,
        'gateway': gateway,
        'order_svc': order_svc,
        'cs': cs
    }


@pytest.fixture
def sample_products(products):
    p1 = Product(id=str(uuid.uuid4()), name="T1", description="d1", price_cents=1000, stock_qty=10)
    p2 = Product(id=str(uuid.uuid4()), name="T2", description="d2", price_cents=2000, stock_qty=5)
    products.add(p1)
    products.add(p2)
    return p1, p2
