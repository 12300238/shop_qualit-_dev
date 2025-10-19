import pytest
from shop import Product


def test_auth_register_login_logout(services, users, sessions):
    auth = services['auth']
    user = auth.register("test@x.com", "pwd", "FN", "LN", "addr")
    assert users.get_by_email("test@x.com") is user
    token = auth.login("test@x.com", "pwd")
    assert sessions.get_user_id(token) == user.id
    auth.logout(token)
    assert sessions.get_user_id(token) is None


def test_cart_service_and_total(services, sample_products):
    p1, p2 = sample_products
    cart_svc = services['cart_svc']
    user_id = "u1"
    cart_svc.add_to_cart(user_id, p1.id, 2)
    cart_svc.add_to_cart(user_id, p2.id, 1)
    total = cart_svc.cart_total(user_id)
    assert total == p1.price_cents*2 + p2.price_cents*1


def test_cart_add_invalid_qty(services, sample_products):
    p1, _ = sample_products
    cart_svc = services['cart_svc']
    with pytest.raises(ValueError):
        cart_svc.add_to_cart("uX", p1.id, 0)


def test_checkout_empty_cart_raises(services):
    order_svc = services['order_svc']
    with pytest.raises(ValueError):
        order_svc.checkout("no_such_user")


def test_password_hasher_and_sessions(users, sessions):
    from shop import PasswordHasher
    ph = PasswordHasher
    h = ph.hash("secret")
    assert isinstance(h, str) and "sha256::" in h
    assert ph.verify("secret", h) is True
    assert ph.verify("bad", h) is False
    # sessions
    token = sessions.create_session("u1")
    assert sessions.get_user_id(token) == "u1"
    sessions.destroy_session(token)
    assert sessions.get_user_id(token) is None


def test_cart_with_inactive_product(services, products):
    cart_svc = services['cart_svc']
    # add inactive product
    from shop import Product
    p = Product(id="ix", name="I", description="d", price_cents=100, stock_qty=5, active=False)
    products.add(p)
    with pytest.raises(ValueError):
        cart_svc.add_to_cart("uX", p.id, 1)


def test_checkout_reserves_stock(services, users, products):
    auth = services['auth']
    cart_svc = services['cart_svc']
    order_svc = services['order_svc']
    p = Product(id="stock_p", name="S", description="d", price_cents=100, stock_qty=3)
    products.add(p)
    user = auth.register("stock@t.com", "pw", "A", "B", "addr")
    cart_svc.add_to_cart(user.id, p.id, 2)
    order = order_svc.checkout(user.id)
    assert products.get(p.id).stock_qty == 1


def test_user_update_and_auth_errors(services, users):
    auth = services['auth']
    # duplicate register should raise
    user = auth.register("dup@x.com", "pw", "A", "B", "addr")
    with pytest.raises(ValueError):
        auth.register("dup@x.com", "pw2", "C", "D", "addr")
    # bad login raises
    with pytest.raises(ValueError):
        auth.login("dup@x.com", "badpw")
    # update_profile: cannot change email or id
    users.add(user)
    user.update_profile(first_name="New", email="hacked@x.com", is_admin=True)
    assert user.first_name == "New"
    assert user.email == "dup@x.com"
    assert user.is_admin is False


def test_pay_by_card_order_not_found_raises(services):
    with pytest.raises(ValueError):
        services['order_svc'].pay_by_card("no-order", "4242", 1, 2030, "123")


def test_cart_remove_and_total_edge_cases(services, products):
    # setup product and cart
    from shop import Product
    p = Product(id="p_rm", name="RM", description="d", price_cents=250, stock_qty=5)
    products.add(p)
    cs = services['cart_svc']
    uid = "u_rm"
    # remove non-existent should be no-op
    cs.remove_from_cart(uid, p.id, 1)
    # add and remove normally
    cs.add_to_cart(uid, p.id, 2)
    cs.remove_from_cart(uid, p.id, 1)
    cart = cs.view_cart(uid)
    assert cart.items[p.id].quantity == 1
    # remove with qty <=0 should delete
    cs.remove_from_cart(uid, p.id, 0)
    assert p.id not in cs.view_cart(uid).items


def test_cart_total_with_missing_and_inactive(services, products):
    from shop import Product
    p1 = Product(id="tot1", name="T1", description="d", price_cents=100, stock_qty=5)
    p2 = Product(id="tot2", name="T2", description="d", price_cents=200, stock_qty=5, active=False)
    products.add(p1)
    products.add(p2)
    uid = "u_tot"
    cs = services['cart_svc']
    # simulate items in cart directly (add_to_cart rejects inactive products)
    from shop import CartItem
    cart = cs.view_cart(uid)
    cart.items[p1.id] = CartItem(product_id=p1.id, quantity=1)
    cart.items[p2.id] = CartItem(product_id=p2.id, quantity=1)
    # remove product p1 from repo to simulate missing
    products._by_id.pop(p1.id)
    total = cs.cart_total(uid)
    # both products are ignored (one missing, one inactive)
    assert total == 0


def test_cart_add_existing_and_remove_delete(services, products):
    # ensure adding existing increases quantity branch (line ~109)
    from shop import Product
    p = Product(id="p_exist", name="E", description="d", price_cents=100, stock_qty=5)
    products.add(p)
    cs = services['cart_svc']
    uid = "u_exist"
    cs.add_to_cart(uid, p.id, 1)
    cs.add_to_cart(uid, p.id, 2)
    cart = cs.view_cart(uid)
    assert cart.items[p.id].quantity == 3


def test_cart_remove_entire_entry_when_qty_le_zero(services, products):
    # exercise Cart.remove branch where qty <=0 deletes the entry (line ~121)
    from shop import Product
    p = Product(id="p_rm2", name="R2", description="d", price_cents=50, stock_qty=5)
    products.add(p)
    cs = services['cart_svc']
    uid = "u_rm2"
    cs.add_to_cart(uid, p.id, 3)
    cs.remove_from_cart(uid, p.id, 0)
    assert p.id not in cs.view_cart(uid).items


def test_cart_add_raises_when_not_enough_stock(services, products):
    from shop import Product
    p = Product(id="p_low", name="Low", description="d", price_cents=100, stock_qty=1)
    products.add(p)
    cs = services['cart_svc']
    # adding more than stock should raise
    with pytest.raises(ValueError):
        cs.add_to_cart("u_low", p.id, 2)


def test_cart_remove_deletes_when_quantity_becomes_zero(services, products):
    from shop import Product
    p = Product(id="p_zero", name="Z", description="d", price_cents=10, stock_qty=5)
    products.add(p)
    cs = services['cart_svc']
    uid = "u_zero"
    cs.add_to_cart(uid, p.id, 1)
    # remove exactly 1 -> quantity becomes 0 and entry removed (line ~126)
    cs.remove_from_cart(uid, p.id, 1)
    assert p.id not in cs.view_cart(uid).items


def test_catalog_list_products_returns_only_active(services, products):
    catalog = services['catalog']
    from shop import Product
    a = Product(id="cat1", name="A", description="d", price_cents=10, stock_qty=1, active=True)
    b = Product(id="cat2", name="B", description="d", price_cents=20, stock_qty=1, active=False)
    products.add(a)
    products.add(b)
    res = catalog.list_products()
    assert a in res and b not in res
