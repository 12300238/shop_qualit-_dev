import streamlit as st
from streamlit_option_menu import option_menu
import requests
import datetime

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
if "users" not in st.session_state:
    st.session_state["users"] = None

# --- Barre latérale ---
with st.sidebar:
    menu_options = ["Accueil", "Connexion", "Panier", "Commandes", "Support"]
    menu_icons = ["house", "person", "cart", "truck", "chat"]

    if st.session_state.get("is_admin", False):
        menu_options.append("Admin")
        menu_icons.append("tools")

    selected = option_menu(
        menu_title="Menu",
        options=menu_options,
        icons=menu_icons,
        menu_icon="list",
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
                # Récupération de l'user
                st.session_state["users"] = requests.get(f"{API_URL}/users_id/{email}").json()
                st.session_state["is_admin"] = st.session_state["users"]["is_admin"]
                st.session_state["token"] = token
                # On récupère l'user via un GET par email (simplifié)
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
                            resp = requests.get(f"{API_URL}/products/{item['product_id']}")
                            if resp.status_code != 200:
                                st.error(f"Erreur API ({resp.status_code})")
                            else:
                                produit = resp.json()
                                st.write(f"🛍️ Produit: `{produit['name']}` | Qté: {item['quantity']}")
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
                commandes = sorted(commandes, key=lambda c: c.get("created_at", 0), reverse=True)
                if commandes:
                    for cmd in commandes:
                        st.write(f"### Commande {cmd['id']}")

                        # --- Décodage du statut (car API renvoie des entiers) ---
                        status_raw = cmd.get("status")
                        status_map = {
                            1: "CREE",
                            2: "VALIDEE",
                            3: "PAYEE",
                            4: "EXPEDIEE",
                            5: "LIVREE",
                            6: "ANNULEE",
                            7: "REMBOURSEE"
                        }
                        status_value = status_map.get(status_raw, str(status_raw))
                        st.write(f"**Statut :** {status_value}")

                        # --- Affichage des items de la commande ---
                        if "items" in cmd:
                            total = 0
                            for item in cmd["items"]:
                                line_total = (item["unit_price_cents"] * item["quantity"]) / 100
                                total += line_total
                                st.markdown(f"- 🛒 `{item['name']}` × {item['quantity']} – {line_total:.2f} €")
                            st.write(f"**💰 Total : {total:.2f} €**")

                        # --- Formulaire de paiement et annulation pour commandes CREE/VALIDEE ---
                        if status_value in ["CREE", "VALIDEE"]:
                            col1, col2 = st.columns(2)

                            # --------- Colonne 1 : Paiement ---------
                            with col1:
                                with st.expander("💳 Payer cette commande"):
                                    st.info("Entrez vos informations de carte pour effectuer le paiement.")
                                    card_number = st.text_input("Numéro de carte (16 chiffres)", key=f"card_{cmd['id']}")
                                    exp_month = st.selectbox(
                                        "Mois d'expiration (MM)",
                                        options=[""] + [f"{m:02d}" for m in range(1, 13)],
                                        key=f"exp_m_{cmd['id']}"
                                    )

                                    current_year = datetime.datetime.now().year
                                    exp_year = st.selectbox(
                                        "Année d'expiration (YYYY)",
                                        options=[""] + [str(y) for y in range(current_year, current_year + 10)],
                                        key=f"exp_y_{cmd['id']}"
                                    )

                                    cvc = st.text_input("CVC (3 chiffres)", type="password", key=f"cvc_{cmd['id']}")

                                    if st.button(f"💰 Confirmer le paiement ({cmd['id']})", key=f"pay_{cmd['id']}"):
                                        now = datetime.datetime.now()
                                        current_year = now.year
                                        current_month = now.month

                                        # Vérifications des champs
                                        if not card_number or not cvc or len(card_number) < 12 or len(cvc) != 3:
                                            st.warning("Veuillez saisir des informations de carte valides.")
                                        elif int(exp_year) < current_year or (int(exp_year) == current_year and int(exp_month) < current_month):
                                            st.error("❌ Cette carte est expirée. Veuillez utiliser une autre carte.")
                                        else:
                                            pay = {
                                                "order_id": cmd["id"],
                                                "card_number": card_number.strip(),
                                                "exp_month": int(exp_month),
                                                "exp_year": int(exp_year),
                                                "cvc": cvc.strip()
                                            }
                                            r = requests.post(f"{API_URL}/orders/pay", json=pay)
                                            if r.status_code == 200:
                                                st.success("Paiement réussi 💳")
                                                st.rerun()
                                            else:
                                                st.error(r.json().get("detail", "Erreur de paiement"))

                            # --------- Colonne 2 : Annulation ---------
                            with col2:
                                with st.expander("❌ Annuler cette commande"):
                                    st.warning("Cette action est irréversible. La commande sera annulée et les stocks remis à jour.")
                                    confirm_key = f"confirm_cancel_{cmd['id']}"
                                    if confirm_key not in st.session_state:
                                        st.session_state[confirm_key] = False

                                    # 1️⃣ Étape 1 : Clic sur "Annuler"
                                    if st.button(f"🗑️ Annuler la commande ({cmd['id']})", key=f"cancel_{cmd['id']}"):
                                        st.session_state[confirm_key] = True

                                    # 2️⃣ Étape 2 : Si l'utilisateur a cliqué, afficher la confirmation
                                    if st.session_state[confirm_key]:
                                        st.error("⚠️ Voulez-vous vraiment annuler cette commande ?")
                                        col_c1, col_c2 = st.columns(2)
                                        with col_c1:
                                            if st.button("✅ Oui, annuler", key=f"confirm_yes_{cmd['id']}"):
                                                cancel_url = f"{API_URL}/orders/cancel"
                                                params = {"user_id": user_id, "order_id": cmd["id"]}
                                                r = requests.delete(cancel_url, params=params)
                                                if r.status_code == 200:
                                                    st.success("Commande annulée ❌")
                                                    st.session_state[confirm_key] = False
                                                    st.rerun()
                                                else:
                                                    st.error(r.json().get("detail", "Erreur lors de l'annulation."))
                                        with col_c2:
                                            if st.button("❌ Non, garder", key=f"confirm_no_{cmd['id']}"):
                                                st.session_state[confirm_key] = False

                        # --- Statuts post-paiement ---
                        else:
                            if status_value == "PAYEE":
                                st.success("✅ Commande payée, en attente d'expédition.")
                            elif status_value == "EXPEDIEE":
                                st.info("📦 Commande expédiée.")
                            elif status_value == "LIVREE":
                                st.success("📬 Commande livrée.")
                            elif status_value == "ANNULEE":
                                st.warning("❌ Commande annulée.")
                            elif status_value == "REMBOURSEE":
                                st.info("💸 Commande remboursée.")

                        st.write("---")
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
    st.subheader("🎫 Support client")

    if not st.session_state["user_id"]:
        st.warning("Connectez-vous pour accéder au support.")
    else:
        user_id = st.session_state["user_id"]
        user_i=requests.get(f"{API_URL}/users_id/{user_id}").json()['id']

        # --- Création d'un nouveau ticket ---
        st.markdown("### 📬 Créer un nouveau ticket")

        subject = st.text_input("Objet du ticket")
        message = st.text_area("Décrivez votre problème :", placeholder="Expliquez votre situation ici...")

        if st.button("📨 Créer le ticket"):
            if not subject.strip():
                st.warning("Veuillez entrer un objet de ticket.")
            elif not message.strip():
                st.warning("Veuillez écrire un message avant d’envoyer.")
            else:
                try:
                    # 🧩 1️⃣ Création du thread
                    payload_thread = {
                        "user_id": user_id,
                        "order_id": None,
                        "subject": subject.strip()
                    }
                    thread_resp = requests.post(f"{API_URL}/threads/open", json=payload_thread)

                    if thread_resp.status_code == 200:
                        thread = thread_resp.json()
                        thread_id = thread["id"]

                        # 🧩 2️⃣ Ajout du premier message

                        payload_message = {
                            "thread_id": thread_id,
                            "author_user_id": user_i,
                            "body": message.strip()
                        }
                        msg_resp = requests.post(f"{API_URL}/threads/post", json=payload_message)


                        if msg_resp.status_code == 200:
                            st.success("✅ Ticket créé avec succès !")
                            st.rerun()
                        else:
                            st.error(msg_resp.json().get("detail", "Erreur lors de l'envoi du message."))
                    else:
                        st.error(thread_resp.json().get("detail", "Erreur lors de la création du ticket."))

                except Exception as e:
                    st.error(f"Impossible de contacter l'API : {e}")

        st.divider()
        st.markdown("### 📋 Vos tickets")
        # --- La suite de ton code support existant (liste + messages) reste inchangée ---


        # --- Liste des threads de l'utilisateur ---
        try:
            resp = requests.get(f"{API_URL}/threads/{user_id}")
            if resp.status_code == 200:
                threads = resp.json()
                if threads:
                    # Trier du plus récent au plus ancien
                    threads = sorted(threads, key=lambda t: t.get("created_at", 0), reverse=True)

                    for th in threads:
                        with st.expander(f"🎟️ {th['subject']} {'(Fermé)' if th.get('closed') else ''}"):
                            st.write(f"📅 Créé le : {datetime.datetime.fromtimestamp(th['created_at']).strftime('%d/%m/%Y %H:%M')}")
                            st.markdown("---")

                            # --- Affichage des messages du thread ---
                            for msg in th['messages']:
                                sender = "🧑 Vous" if msg["author_user_id"] == user_i else "🎧 Support"
                                date = datetime.datetime.fromtimestamp(msg["created_at"]).strftime("%d/%m/%Y %H:%M")
                                st.markdown(f"**{sender}** ({date}) :\n> {msg['body']}")

                            # --- Envoi d’un nouveau message ---
                            if not th.get("closed", False):
                                new_msg = st.text_area("✉️ Votre réponse :", key=f"msg_{th['id']}")
                                if st.button("Envoyer", key=f"send_{th['id']}"):
                                    if not new_msg.strip():
                                        st.warning("Votre message est vide.")
                                    else:
                                        payload = {
                                            "thread_id": th["id"],
                                            "author_user_id": user_i,
                                            "body": new_msg.strip()
                                        }
                                        r = requests.post(f"{API_URL}/threads/post", json=payload)
                                        if r.status_code == 200:
                                            st.success("Message envoyé ✅")
                                            st.rerun()
                                        else:
                                            st.error(r.json().get("detail", "Erreur lors de l'envoi du message."))
                            else:
                                st.info("🔒 Ce ticket est fermé, vous ne pouvez plus répondre.")
                else:
                    st.info("Aucun ticket trouvé.")
            else:
                st.error("Erreur lors du chargement des tickets.")
        except Exception as e:
            st.error(f"API non disponible : {e}")



#lui redonner la liste des fichier

# gerer les threads dans la page support

# modifier le statut des tickets (ouvert/ferme)

# a la création d'un produit rendre inmpossible son activation si le stock est a 0

# suprimer un produit dans la page admin