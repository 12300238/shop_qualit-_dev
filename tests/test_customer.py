import pytest


def test_customer_threads(services, users):
    cs = services['cs']
    auth = services['auth']
    user = auth.register("c2@x.com", "pw", "A", "B", "addr")
    th = cs.open_thread(user.id, "Sujet", None)
    assert th.user_id == user.id
    msg = cs.post_message(th.id, user.id, "Bonjour")
    assert msg.body == "Bonjour"
    # attempt close by non-admin should raise
    with pytest.raises(PermissionError):
        cs.close_thread(th.id, user.id)
    # admin can close
    admin = auth.register("admin2@x.com", "pw", "Adm", "I", "addr", is_admin=True)
    closed = cs.close_thread(th.id, admin.id)
    assert closed.closed is True


def test_post_message_unknown_author_raises(services):
    cs = services['cs']
    auth = services['auth']
    user = auth.register("c3@x.com", "pw", "A", "B", "addr")
    th = cs.open_thread(user.id, "Help", None)
    # posting with a non-existing user id should raise
    with pytest.raises(ValueError):
        cs.post_message(th.id, "nope", "Hi")


def test_messages_order_and_multi_posts(services):
    cs = services['cs']
    auth = services['auth']
    user = auth.register("m1@x.com", "pw", "A", "B", "addr")
    th = cs.open_thread(user.id, "Order", None)
    m1 = cs.post_message(th.id, user.id, "First")
    m2 = cs.post_message(th.id, None, "Agent reply")
    m3 = cs.post_message(th.id, user.id, "Thanks")
    assert [m.body for m in th.messages] == ["First", "Agent reply", "Thanks"]


def test_close_thread_missing_and_list_by_user(services):
    cs = services['cs']
    auth = services['auth']
    user = auth.register("tlist@x.com", "pw", "A", "B", "addr")
    # list_by_user should be empty initially
    threads = cs.threads.list_by_user(user.id)
    assert threads == []
    # closing a non-existent thread should raise (admin required first)
    admin = auth.register("admin-tlist@x.com", "pw", "Adm", "I", "addr", is_admin=True)
    with pytest.raises(ValueError):
        cs.close_thread("no-thread", admin.id)
