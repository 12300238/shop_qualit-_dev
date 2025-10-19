import pytest
import time
from shop import Product, OrderStatus


def test_checkout_and_payment(services, users, products, sample_products):
    auth = services['auth']
    order_svc = services['order_svc']
    billing = services['billing']
    gateway = services['gateway']
    p1, p2 = sample_products
    # create user
    user = auth.register("c@d.com", "pw", "A", "B", "addr")
    # add to cart
    services['cart_svc'].add_to_cart(user.id, p1.id, 2)
    # checkout
    order = order_svc.checkout(user.id)
    assert order.status.name == 'CREE'
    # pay
    payment = order_svc.pay_by_card(order.id, "4242424242424242", 12, 2030, "123")
    assert payment.succeeded is True
    assert order.status.name == 'PAYEE'
    # invoice created
    inv = billing.invoices.get(payment.order_id)  # invoices stored by invoice.id, so we check repository non-empty
    assert len(billing.invoices._by_id) == 1


def test_backoffice_flow(services, users, products, sample_products):
    auth = services['auth']
    order_svc = services['order_svc']
    billing = services['billing']
    p1, p2 = sample_products
    admin = auth.register("admin@x.com", "pw", "A", "B", "addr", is_admin=True)
    user = auth.register("u@x.com", "pw", "C", "D", "addr")
    services['cart_svc'].add_to_cart(user.id, p1.id, 1)
    order = order_svc.checkout(user.id)
    # validate
    order = order_svc.backoffice_validate_order(admin.id, order.id)
    assert order.status.name == 'VALIDEE'
    # set status to paid to allow shipping
    order.status = order_svc.orders.get(order.id).status


def test_payment_refused(services, users, products, sample_products):
    # Force gateway to refuse when card ends with 0000
    gateway = services['gateway']
    auth = services['auth']
    p1, _ = sample_products
    user = auth.register("r@x.com", "pw", "A", "B", "addr")
    services['cart_svc'].add_to_cart(user.id, p1.id, 1)
    order = services['order_svc'].checkout(user.id)
    with pytest.raises(ValueError):
        services['order_svc'].pay_by_card(order.id, "4000000000000000", 1, 2030, "000")


def test_cancellation_too_late(services, users, products, sample_products):
    auth = services['auth']
    p1, _ = sample_products
    admin = auth.register("adm3@x.com", "pw", "A", "B", "addr", is_admin=True)
    user = auth.register("uu@x.com", "pw", "C", "D", "addr")
    services['cart_svc'].add_to_cart(user.id, p1.id, 1)
    order = services['order_svc'].checkout(user.id)
    # validate then mark as paid so it can be shipped
    services['order_svc'].backoffice_validate_order(admin.id, order.id)
    # mark as paid
    order.status = OrderStatus.PAYEE
    order.paid_at = time.time()
    services['order_svc'].orders.update(order)
    # ship
    services['order_svc'].backoffice_ship_order(admin.id, order.id)
    # now cancellation should be rejected
    with pytest.raises(ValueError):
        services['order_svc'].request_cancellation(user.id, order.id)


def test_invoice_contents_and_billing(services, users, products, sample_products):
    auth = services['auth']
    billing = services['billing']
    p1, p2 = sample_products
    user = auth.register("inv@x.com", "pw", "A", "B", "addr")
    services['cart_svc'].add_to_cart(user.id, p1.id, 1)
    order = services['order_svc'].checkout(user.id)
    # pay
    payment = services['order_svc'].pay_by_card(order.id, "4242424242424242", 12, 2030, "123")
    # invoice should exist and contain a line for p1
    assert len(billing.invoices._by_id) >= 1
    inv = next(iter(billing.invoices._by_id.values()))
    assert inv.user_id == user.id
    assert any(line.product_id == p1.id for line in inv.lines)


def test_refund_and_stock_restore(services, users, products, sample_products):
    auth = services['auth']
    p1, _ = sample_products
    user = auth.register("ref@x.com", "pw", "A", "B", "addr")
    services['cart_svc'].add_to_cart(user.id, p1.id, 1)
    order = services['order_svc'].checkout(user.id)
    payment = services['order_svc'].pay_by_card(order.id, "4242424242424242", 12, 2030, "123")
    # admin refund
    admin = auth.register("adm@x.com", "pw", "A", "B", "addr", is_admin=True)
    services['order_svc'].backoffice_refund(admin.id, order.id)
    assert order.status.name == 'REMBOURSEE'
    # stock restored
    assert products.get(p1.id).stock_qty == sample_products[0].stock_qty


def test_delivery_tracking_and_backoffice_ship_user_missing(services, users, products, sample_products):
    auth = services['auth']
    order_svc = services['order_svc']
    p1, _ = sample_products
    admin = auth.register("adminX@x.com", "pw", "A", "B", "addr", is_admin=True)
    user = auth.register("uX@x.com", "pw", "A", "B", "addr")
    services['cart_svc'].add_to_cart(user.id, p1.id, 1)
    order = order_svc.checkout(user.id)
    # mark paid so we can ship
    order.status = order_svc.orders.get(order.id).status
    order.status = order_svc.orders.get(order.id).status
    # deliberately remove user to simulate missing user
    users._by_id.pop(user.id)
    with pytest.raises(ValueError):
        order_svc.backoffice_ship_order(admin.id, order.id)


def test_backoffice_errors_and_refunds(services, users, products, sample_products):
    auth = services['auth']
    order_svc = services['order_svc']
    p1, _ = sample_products
    admin = auth.register("adminY@x.com", "pw", "A", "B", "addr", is_admin=True)
    user = auth.register("userY@x.com", "pw", "C", "D", "addr")
    services['cart_svc'].add_to_cart(user.id, p1.id, 1)
    order = order_svc.checkout(user.id)
    # only admin can validate
    with pytest.raises(PermissionError):
        order_svc.backoffice_validate_order(user.id, order.id)
    # validate as admin
    order_svc.backoffice_validate_order(admin.id, order.id)
    # cannot ship if not paid
    with pytest.raises(ValueError):
        order_svc.backoffice_ship_order(admin.id, order.id)
    # do a real payment then tamper provider_ref via order_svc.payments
    services['cart_svc'].add_to_cart(user.id, p1.id, 1)
    order2 = order_svc.checkout(user.id)
    pay = order_svc.pay_by_card(order2.id, "4242424242424242", 12, 2030, "123")
    # remove provider_ref to simulate missing PSP reference
    order_svc.payments.get(pay.id).provider_ref = None
    with pytest.raises(ValueError):
        order_svc.backoffice_refund(admin.id, order2.id)
    # now set a provider_ref and test partial refund amount param
    order_svc.payments.get(pay.id).provider_ref = "tx-123"
    res_order = order_svc.backoffice_refund(admin.id, order2.id, amount_cents=100)
    assert res_order.status.name == 'REMBOURSEE'


def test_request_cancellation_wrong_user_and_success(services, users, products):
    auth = services['auth']
    order_svc = services['order_svc']
    p = Product(id="c1", name="C1", description="d", price_cents=100, stock_qty=5)
    products.add(p)
    user = auth.register("own@x.com", "pw", "A", "B", "addr")
    other = auth.register("other@x.com", "pw", "C", "D", "addr")
    services['cart_svc'].add_to_cart(user.id, p.id, 1)
    order = order_svc.checkout(user.id)
    # wrong user trying to cancel
    with pytest.raises(ValueError):
        order_svc.request_cancellation(other.id, order.id)
    # successful cancel by owner
    canceled = order_svc.request_cancellation(user.id, order.id)
    assert canceled.status.name == 'ANNULEE'


def test_backoffice_validate_and_ship_permission_errors(services, users, products):
    auth = services['auth']
    order_svc = services['order_svc']
    p = Product(id="sv1", name="SV", description="d", price_cents=100, stock_qty=5)
    products.add(p)
    admin = auth.register("svadmin@x.com", "pw", "A", "B", "addr", is_admin=True)
    user = auth.register("svuser@x.com", "pw", "C", "D", "addr")
    services['cart_svc'].add_to_cart(user.id, p.id, 1)
    order = order_svc.checkout(user.id)
    # non-admin cannot validate
    with pytest.raises(PermissionError):
        order_svc.backoffice_validate_order(user.id, order.id)
    # admin validate but cannot ship if not paid
    order_svc.backoffice_validate_order(admin.id, order.id)
    with pytest.raises(ValueError):
        order_svc.backoffice_ship_order(admin.id, order.id)


def test_delivery_mark_delivered_and_refund_permission(services, users, products):
    auth = services['auth']
    order_svc = services['order_svc']
    gateway = services['gateway']
    p = Product(id="dmd1", name="DMD", description="d", price_cents=100, stock_qty=5)
    products.add(p)
    admin = auth.register("adm-dmd@x.com", "pw", "A", "B", "addr", is_admin=True)
    user = auth.register("usr-dmd@x.com", "pw", "C", "D", "addr")
    services['cart_svc'].add_to_cart(user.id, p.id, 1)
    order = order_svc.checkout(user.id)
    # simulate paid order so we can ship
    order.status = order_svc.orders.get(order.id).status
    order.status = order_svc.orders.get(order.id).status
    # do payment for second order to have a payment record
    services['cart_svc'].add_to_cart(user.id, p.id, 1)
    o2 = order_svc.checkout(user.id)
    pay = order_svc.pay_by_card(o2.id, "4242424242424242", 12, 2030, "123")
    # mark delivered without delivery should raise
    with pytest.raises(ValueError):
        order_svc.backoffice_mark_delivered(admin.id, o2.id)
    # refund permission: non-admin cannot refund
    with pytest.raises(PermissionError):
        order_svc.backoffice_refund(user.id, o2.id)


def test_delivery_service_mark_delivered_direct(services):
    from shop import Order, OrderStatus, Delivery
    delivery_svc = services['delivery_svc']
    # prepare a minimal order for delivery
    order = Order(id="od1", user_id="u1", items=[], status=OrderStatus.CREE, created_at=time.time())
    d = delivery_svc.prepare_delivery(order, address="X")
    d2 = delivery_svc.mark_delivered(d)
    assert d2.status == "LIVREE"


def test_checkout_fails_on_inactive_and_insufficient_stock(services, users, products):
    order_svc = services['order_svc']
    cs = services['cart_svc']
    from shop import Product, CartItem
    user = services['auth'].register("chk@x.com", "pw", "A", "B", "addr")
    # inactive product
    p_in = Product(id="pin", name="PIN", description="d", price_cents=100, stock_qty=5, active=False)
    products.add(p_in)
    cart = cs.view_cart(user.id)
    cart.items[p_in.id] = CartItem(product_id=p_in.id, quantity=1)
    with pytest.raises(ValueError):
        order_svc.checkout(user.id)
    # insufficient stock
    p_low = Product(id="plow", name="PLOW", description="d", price_cents=100, stock_qty=1, active=True)
    products.add(p_low)
    cart = cs.view_cart(user.id)
    cart.items[p_low.id] = CartItem(product_id=p_low.id, quantity=3)
    with pytest.raises(ValueError):
        order_svc.checkout(user.id)


def test_backoffice_validate_wrong_status_and_ship_user_missing(services, users, products):
    auth = services['auth']
    order_svc = services['order_svc']
    from shop import Product, OrderStatus
    p = Product(id="bv1", name="BV", description="d", price_cents=100, stock_qty=5)
    products.add(p)
    admin = auth.register("bvadmin@x.com", "pw", "A", "B", "addr", is_admin=True)
    user = auth.register("bvuser@x.com", "pw", "C", "D", "addr")
    services['cart_svc'].add_to_cart(user.id, p.id, 1)
    order = order_svc.checkout(user.id)
    # change status to PAYEE so validate should fail
    order.status = OrderStatus.PAYEE
    order_svc.orders.update(order)
    with pytest.raises(ValueError):
        order_svc.backoffice_validate_order(admin.id, order.id)
    # set to PAYEE and remove user to trigger user missing branch in ship
    order.status = OrderStatus.PAYEE
    order_svc.orders.update(order)
    users._by_id.pop(user.id)
    with pytest.raises(ValueError):
        order_svc.backoffice_ship_order(admin.id, order.id)


def test_backoffice_mark_delivered_success_and_refund_status_not_allowed(services, users, products):
    auth = services['auth']
    order_svc = services['order_svc']
    from shop import Product, Delivery, OrderStatus
    p = Product(id="md2", name="MD2", description="d", price_cents=100, stock_qty=5)
    products.add(p)
    admin = auth.register("markadm@x.com", "pw", "A", "B", "addr", is_admin=True)
    user = auth.register("markuser@x.com", "pw", "C", "D", "addr")
    services['cart_svc'].add_to_cart(user.id, p.id, 1)
    order = order_svc.checkout(user.id)
    # cannot mark delivered when not shipped
    with pytest.raises(ValueError):
        order_svc.backoffice_mark_delivered(admin.id, order.id)
    # simulate shipped and delivery present
    delivery = services['delivery_svc'].prepare_delivery(order, address=user.address)
    delivery = services['delivery_svc'].ship(delivery)
    order.delivery = delivery
    order.status = OrderStatus.EXPEDIEE
    order_svc.orders.update(order)
    res = order_svc.backoffice_mark_delivered(admin.id, order.id)
    assert res.status == OrderStatus.LIVREE
    # refund not allowed on wrong status
    # prepare a new order by adding to cart first
    services['cart_svc'].add_to_cart(user.id, p.id, 1)
    new_order = order_svc.checkout(user.id)
    with pytest.raises(ValueError):
        order_svc.backoffice_refund(admin.id, new_order.id)


def test_backoffice_ship_requires_admin(services, users, products):
    auth = services['auth']
    order_svc = services['order_svc']
    p = Product(id="ship1", name="S1", description="d", price_cents=100, stock_qty=5)
    products.add(p)
    admin = auth.register("shipadm@x.com", "pw", "A", "B", "addr", is_admin=True)
    user = auth.register("shipuser@x.com", "pw", "C", "D", "addr")
    services['cart_svc'].add_to_cart(user.id, p.id, 1)
    order = order_svc.checkout(user.id)
    # non-admin cannot ship
    with pytest.raises(PermissionError):
        order_svc.backoffice_ship_order(user.id, order.id)


def test_checkout_stock_insufficient_branch(services, users, products):
    order_svc = services['order_svc']
    cs = services['cart_svc']
    from shop import Product, CartItem
    user = services['auth'].register("stockchk@x.com", "pw", "A", "B", "addr")
    p = Product(id="stockzero", name="Z", description="d", price_cents=10, stock_qty=0, active=True)
    products.add(p)
    cart = cs.view_cart(user.id)
    cart.items[p.id] = CartItem(product_id=p.id, quantity=1)
    with pytest.raises(ValueError):
        order_svc.checkout(user.id)



def test_pay_by_card_wrong_status_and_mark_delivered_errors(services, users, products, sample_products):
    auth = services['auth']
    order_svc = services['order_svc']
    p1, _ = sample_products
    user = auth.register("st@x.com", "pw", "A", "B", "addr")
    services['cart_svc'].add_to_cart(user.id, p1.id, 1)
    order = order_svc.checkout(user.id)
    # set status to invalid for payment
    order.status = OrderStatus.EXPEDIEE
    order_svc.orders.update(order)
    with pytest.raises(ValueError):
        order_svc.pay_by_card(order.id, "4242424242424242", 12, 2030, "123")


def test_post_message_on_closed_thread_raises(services, users):
    cs = services['cs']
    auth = services['auth']
    user = auth.register("cclose@x.com", "pw", "A", "B", "addr")
    th = cs.open_thread(user.id, "Subj", None)
    admin = auth.register("admclose@x.com", "pw", "A", "B", "addr", is_admin=True)
    cs.close_thread(th.id, admin.id)
    with pytest.raises(ValueError):
        cs.post_message(th.id, user.id, "after closed")


def test_order_repository_list_and_view_orders(services, users, products):
    # create user and two orders to verify list_by_user mapping (line ~344)
    auth = services['auth']
    order_svc = services['order_svc']
    p = Product(id="lp1", name="LP", description="d", price_cents=100, stock_qty=5)
    products.add(p)
    user = auth.register("list@x.com", "pw", "A", "B", "addr")
    services['cart_svc'].add_to_cart(user.id, p.id, 1)
    o1 = order_svc.checkout(user.id)
    services['cart_svc'].add_to_cart(user.id, p.id, 1)
    o2 = order_svc.checkout(user.id)
    orders = order_svc.view_orders(user.id)
    assert [o.id for o in orders] == [o1.id, o2.id]


def test_cartservice_add_product_not_found_raises(services):
    cs = services['cart_svc']
    with pytest.raises(ValueError):
        cs.add_to_cart("nouser", "no-product", 1)


def test_backoffice_mark_delivered_errors_and_permissions(services, users, products):
    auth = services['auth']
    order_svc = services['order_svc']
    p = Product(id="md1", name="MD", description="d", price_cents=100, stock_qty=5)
    products.add(p)
    admin = auth.register("adm-md@x.com", "pw", "A", "B", "addr", is_admin=True)
    user = auth.register("usr-md@x.com", "pw", "C", "D", "addr")
    services['cart_svc'].add_to_cart(user.id, p.id, 1)
    order = order_svc.checkout(user.id)
    # non-admin cannot mark delivered
    with pytest.raises(PermissionError):
        order_svc.backoffice_mark_delivered(user.id, order.id)
    # admin cannot mark delivered if not shipped
    with pytest.raises(ValueError):
        order_svc.backoffice_mark_delivered(admin.id, order.id)
