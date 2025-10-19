import streamlit as st
from streamlit_option_menu import option_menu
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Shop Frontend", layout="wide")
st.title("🛍️ Boutique en ligne")

# --- Initialisation du state ---
if "token" not in st.session_state:
    st.session_state["token"] = None
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False

# --- Barre latérale ---
with st.sidebar:
    selected = option_menu(
        menu_title="Menu",  # titre du menu
        options=["Accueil", "Connexion", "Panier", "Commandes", "Support"],
        icons=["house", "person", "cart", "truck", "chat"],
        menu_icon="list",  # icône du menu burger
        default_index=0,
    )

page = selected

# ------------------------------------------------------
#  PAGE : CONNEXION / INSCRIPTION
# ------------------------------------------------------
if page == "Connexion":
    st.subheader("🔑 Connexion ou inscription")

    with st.expander("Connexion existante"):
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Mot de passe", type="password", key="login_password")
        if st.button("Se connecter"):
            payload = {"email": email, "password": password, "first_name": "", "last_name": "", "address": ""}
            r = requests.post(f"{API_URL}/users/login", json=payload)
            if r.status_code == 200:
                token = r.json()["token"]
                # Récupération de l'user_id
                users = requests.get(f"{API_URL}/users")
                st.session_state["token"] = token
                # On récupère l'id via un GET par email (simplifié)
                # (Tu peux améliorer avec une route /me dans l'API)
                st.session_state["user_id"] = email  # temporaire
                st.success("Connexion réussie ✅")
            else:
                st.error(r.json().get("detail", "Erreur de connexion."))

    with st.expander("Créer un compte"):
        email = st.text_input("Email (nouveau compte)", key="reg_email")
        password = st.text_input("Mot de passe", type="password", key="reg_password")
        first_name = st.text_input("Prénom")
        last_name = st.text_input("Nom")
        address = st.text_area("Adresse")
        if st.button("S'inscrire"):
            payload = {
                "email": email,
                "password": password,
                "first_name": first_name,
                "last_name": last_name,
                "address": address,
                "is_admin": False
            }
            r = requests.post(f"{API_URL}/users/register", json=payload)
            if r.status_code == 200:
                st.success("Compte créé avec succès 🎉")
            else:
                st.error(r.json().get("detail", "Erreur d'inscription."))

    if st.session_state["token"]:
        if st.button("Se déconnecter"):
            requests.delete(f"{API_URL}/users/logout", params={"token": st.session_state['token']})
            st.session_state["token"] = None
            st.session_state["user_id"] = None
            st.success("Déconnexion réussie 👋")

# ------------------------------------------------------
#  PAGE : ACCUEIL
# ------------------------------------------------------
elif page == "Accueil":
    st.write("Bienvenue sur le site de la boutique !")
    st.subheader("🛒 Produits disponibles")
    try:
        resp = requests.get(f"{API_URL}/products")
        if resp.status_code == 200:
            produits = resp.json()
            for p in produits:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"### {p['name']}")
                    st.write(p['description'])
                    st.write(f"Prix : {p['price_cents']/100:.2f} € | Stock : {p['stock_qty']}")
                with col2:
                    qty = st.number_input(f"Quantité pour {p['name']}", min_value=1, max_value=p['stock_qty'], key=p['id'])
                    if st.button(f"Ajouter au panier - {p['name']}", key="btn_" + p['id']):
                        if not st.session_state["user_id"]:
                            st.warning("Connectez-vous pour ajouter au panier.")
                        else:
                            payload = {"product_id": p['id'], "quantity": int(qty)}
                            r = requests.post(f"{API_URL}/cart/{st.session_state['user_id']}/add", json=payload)
                            if r.status_code == 200:
                                st.success("Produit ajouté au panier 🛒")
                            else:
                                st.error(r.json().get("detail", "Erreur lors de l'ajout."))
        else:
            st.error("Erreur de chargement des produits.")
    except Exception as e:
        st.error(f"API non disponible: {e}")

# ------------------------------------------------------
#  PAGE : PANIER
# ------------------------------------------------------
elif page == "Panier":
    st.subheader("🧺 Votre panier")
    if not st.session_state["user_id"]:
        st.warning("Connectez-vous d'abord.")
    else:
        user_id = st.session_state["user_id"]
        try:
            # --- Récupération du panier ---
            resp = requests.get(f"{API_URL}/cart/{user_id}")
            if resp.status_code != 200:
                st.error(f"Erreur API ({resp.status_code})")
            else:
                panier = resp.json()

                # Vérifie le format et convertit si besoin
                if isinstance(panier, dict) and "items" in panier:
                    items = panier["items"]
                    if isinstance(items, dict):  # API renvoie souvent un dict {id: {product_id, qty}}
                        items = list(items.values())
                else:
                    st.warning("Panier vide ou format inattendu.")
                    st.stop()

                if not items:
                    st.info("Votre panier est vide.")
                else:
                    for item in items:
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.write(f"🛍️ Produit: `{item['product_id']}` | Qté: {item['quantity']}")
                        with col2:
                            max_qty = max(1, item['quantity'])
                            qty_remove = st.number_input(
                                f"Quantité à retirer ({item['product_id']})",
                                min_value=1,
                                max_value=max_qty,
                                value=1,
                                key=f"qty_rm_{item['product_id']}"
                            )
                        with col3:
                            if st.button("❌ Retirer", key=f"rm_{item['product_id']}"):
                                data = {"product_id": item["product_id"], "quantity": qty_remove}
                                r = requests.delete(f"{API_URL}/cart/{user_id}/remove", json=data)
                                if r.status_code == 200:
                                    st.success("Article supprimé du panier.")
                                    st.rerun()
                                else:
                                    st.error(r.json().get("detail", "Erreur lors de la suppression."))

                    # --- Total du panier ---
                    total_resp = requests.get(f"{API_URL}/cart/{user_id}/total")
                    if total_resp.status_code == 200:
                        total_json = total_resp.json()
                        if isinstance(total_json, dict) and "total_cents" in total_json:
                            st.write(f"**Total: {total_json['total_cents']/100:.2f} €**")

                    # --- Vider le panier entièrement ---
                    if st.button("🗑️ Vider tout le panier"):
                        r = requests.delete(f"{API_URL}/cart/{user_id}/clear")
                        if r.status_code == 200:
                            st.success("Panier vidé.")
                            st.rerun()

                    # --- Passer la commande ---
                    if st.button("✅ Passer la commande"):
                        r = requests.post(f"{API_URL}/orders/checkout/{user_id}")
                        if r.status_code == 200:
                            st.success("Commande créée avec succès !")
                            st.rerun()
                        else:
                            st.error(r.json().get("detail", "Erreur lors du checkout."))
        except Exception as e:
            st.error(f"API non disponible: {e}")


# ------------------------------------------------------
#  PAGE : COMMANDES
# ------------------------------------------------------
elif page == "Commandes":
    st.subheader("📦 Vos commandes")
    if not st.session_state["user_id"]:
        st.warning("Connectez-vous d'abord.")
    else:
        user_id = st.session_state["user_id"]
        try:
            resp = requests.get(f"{API_URL}/orders/{user_id}")
            if resp.status_code == 200:
                commandes = resp.json()
                if commandes:
                    for cmd in commandes:
                        st.write(f"### Commande {cmd['id']} – Statut: {cmd['status']}")
                        if cmd["status"] in ["CREE", "VALIDEE"]:
                            if st.button(f"Payer cette commande ({cmd['id']})"):
                                pay = {
                                    "order_id": cmd["id"],
                                    "card_number": "4111111111111111",
                                    "exp_month": 12,
                                    "exp_year": 2030,
                                    "cvc": "123"
                                }
                                r = requests.post(f"{API_URL}/orders/pay", json=pay)
                                if r.status_code == 200:
                                    st.success("Paiement réussi 💳")
                                else:
                                    st.error(r.json().get("detail", "Erreur de paiement"))
                else:
                    st.info("Aucune commande trouvée.")
            else:
                st.error("Erreur lors du chargement des commandes.")
        except Exception as e:
            st.error(f"API non disponible: {e}")

# ------------------------------------------------------
#  PAGE : SUPPORT
# ------------------------------------------------------
elif page == "Support":
    st.subheader("💬 Support client")
    if not st.session_state["user_id"]:
        st.warning("Connectez-vous d'abord.")
    else:
        user_id = st.session_state["user_id"]
        subject = st.text_input("Sujet du ticket")
        if st.button("Ouvrir un nouveau ticket"):
            r = requests.post(f"{API_URL}/threads/open", json={"user_id": user_id, "subject": subject})
            if r.status_code == 200:
                st.success("Ticket créé ✅")
            else:
                st.error(r.json().get("detail", "Erreur."))
        st.write("---")
        threads = requests.get(f"{API_URL}/threads/{user_id}")
        if threads.status_code == 200:
            for th in threads.json():
                st.write(f"**{th['subject']}** – Fermé : {th['closed']}")
