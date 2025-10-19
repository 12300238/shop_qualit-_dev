import pytest
from shop import User, Product


def test_user_repository_basic(users):
    u = User(id="u1", email="a@b.c", password_hash="h", first_name="A", last_name="B", address="X")
    users.add(u)
    assert users.get("u1") is u
    assert users.get_by_email("A@b.c") is u


def test_product_repository_and_stock(products):
    p = Product(id="p1", name="P", description="d", price_cents=100, stock_qty=2)
    products.add(p)
    assert products.get("p1") is p
    assert products.list_active() == [p]
    products.reserve_stock("p1", 1)
    assert products.get("p1").stock_qty == 1
    products.release_stock("p1", 2)
    assert products.get("p1").stock_qty == 3


def test_cart_repository(carts, products):
    from shop import Product
    p = Product(id="p2", name="PX", description="d", price_cents=500, stock_qty=3)
    products.add(p)
    cart = carts.get_or_create("u1")
    assert cart.user_id == "u1"
    cart.add(p, 2)
    assert cart.items[p.id].quantity == 2
    cart.remove(p.id, 1)
    assert cart.items[p.id].quantity == 1
    cart.remove(p.id, 0)
    assert p.id not in cart.items


def test_reserve_stock_insufficient(products):
    p = Product(id="p3", name="PX", description="d", price_cents=100, stock_qty=1)
    products.add(p)
    with pytest.raises(ValueError):
        products.reserve_stock("p3", 2)


def test_product_inactive_and_release(products):
    p = Product(id="px_inact", name="X", description="d", price_cents=100, stock_qty=5, active=False)
    products.add(p)
    # inactive product should not appear in list_active
    assert p not in products.list_active()
    # reserve on inactive currently does not check 'active' and will decrement stock
    products.reserve_stock("px_inact", 1)
    assert products.get("px_inact").stock_qty == 4
    # releasing stock for a missing product should not raise
    products.release_stock("nonexistent", 3)


def test_reserve_release_edge_cases(products):
    p = Product(id="p4", name="P4", description="d", price_cents=50, stock_qty=2)
    products.add(p)
    # reserve zero should be a no-op or allowed; implementation treats it as success
    products.reserve_stock("p4", 0)
    assert products.get("p4").stock_qty == 2
    # reserve negative currently increases stock (implementation subtracts qty)
    products.reserve_stock("p4", -1)
    assert products.get("p4").stock_qty == 3
