import streamlit as st
from streamlit_option_menu import option_menu
import requests
import datetime
import re
import json

API_URL = "http://api:8000"


# --- Configuration de la page principale ---
st.set_page_config(page_title="Shop Frontend", layout="wide")
st.title("🛍️ Boutique en ligne")

# --- Initialisation de l’état utilisateur (session) ---
if "token" not in st.session_state:
    st.session_state["token"] = None
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False
if "users" not in st.session_state:
    st.session_state["users"] = None

# --- Barre latérale / Menu principal ---
with st.sidebar:
    menu_options = ["Accueil", "Profil", "Panier", "Commandes", "Support"]
    menu_icons = ["house", "person", "cart", "truck", "chat"]

    # Si l’utilisateur est administrateur, on ajoute le menu “Admin”
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


# ======================================================
#  PAGE : PROFIL — Connexion, inscription, modification
# ======================================================
if page == "Profil":
    st.subheader("👤 Mon profil")

    # --- SECTION CONNEXION UTILISATEUR ---
    if not st.session_state["token"]:
        with st.expander("Connexion"):
            email_login = st.text_input("Email", key="login_email")
            pwd_login = st.text_input("Mot de passe", type="password", key="login_password")

            # --- Bouton de connexion ---
            if st.button("Se connecter"):
                payload = {"email": email_login, "password": pwd_login,
                           "first_name": "", "last_name": "", "address": ""}
                r = requests.post(f"{API_URL}/users/login", json=payload)

                if r.status_code == 200:
                    token = r.json()["token"]
                    user_obj = requests.get(f"{API_URL}/users_id/{email_login}").json()
                    st.session_state.update({
                        "token": token,
                        "users": user_obj,
                        "user_id": user_obj["id"],
                        "is_admin": user_obj["is_admin"]
                    })
                    st.success("Connexion réussie ✅")
                    st.rerun()
                else:
                    st.error(r.json().get("detail", "Erreur de connexion."))

        st.divider()

        # --- FORMULAIRE D’INSCRIPTION ---
        with st.expander("Créer un compte"):
            email_reg = st.text_input("Email")
            pwd_reg = st.text_input("Mot de passe", type="password")
            first_name_reg = st.text_input("Prénom")
            last_name_reg = st.text_input("Nom")
            num_reg = st.text_input("Numéro de rue")
            street_reg = st.text_input("Rue")
            cp_reg = st.text_input("Code postal")
            city_reg = st.text_input("Ville")

            # --- Bouton de création de compte ---
            if st.button("Créer mon compte"):
                # Vérification des champs obligatoires
                if not (email_reg and pwd_reg and first_name_reg and last_name_reg and num_reg and street_reg and cp_reg and city_reg):
                    st.error("Veuillez remplir tous les champs.")
                    st.stop()

                # Validation de chaque champ (regex)
                if not re.match(r"^((?!\.)[\w\-_.]*[^.])(@\w+)(\.\w+(\.\w+)?[^.\W])$", email_reg.strip()):
                    st.error("Email invalide.")
                    st.stop()
                if not re.match(r"^[0-9]{1,4}[A-Za-z]?$", num_reg.strip()):
                    st.error("Numéro de rue invalide.")
                    st.stop()
                if not re.match(r"^[A-Za-zÀ-ÿ0-9'’\-\.\s]{3,}$", street_reg.strip()):
                    st.error("Nom de rue invalide.")
                    st.stop()
                if not re.match(r"^[0-9]{5}$", cp_reg.strip()):
                    st.error("Code postal invalide.")
                    st.stop()
                if not re.match(r"^[A-Za-zÀ-ÿ'’\-\.\s]{2,}$", city_reg.strip()):
                    st.error("Nom de ville invalide.")
                    st.stop()

                # Construction de l’adresse complète
                address_full = f"{num_reg.strip()} {street_reg.strip()} {cp_reg.strip()} {city_reg.strip()}"

                # Données envoyées à l’API d’inscription
                payload = {
                    "email": email_reg,
                    "password": pwd_reg,
                    "first_name": first_name_reg,
                    "last_name": last_name_reg,
                    "address": address_full
                }

                # Appel API création de compte
                r = requests.post(f"{API_URL}/users/register", json=payload)

                if r.status_code == 200:
                    st.success("✅ Compte créé, vous pouvez vous connecter !")
                else:
                    st.error(r.json().get("detail", "Erreur lors de l'inscription."))

    # --- SECTION PROFIL UTILISATEUR CONNECTÉ ---
    else:
        user = st.session_state["users"]

        st.write(f"**Email :** {user['email']}")
        st.write(f"**Admin :** {'✅ Oui' if user['is_admin'] else '❌ Non'}")
        st.divider()

        st.markdown("### ✏️ Modifier mes informations")

        # --- Pré-remplissage des champs d’adresse ---
        parts = user["address"].split(" ")
        num_init = parts[0]
        cp_init = parts[-2]
        city_init = " ".join(parts[-1:])
        street_init = " ".join(parts[1:-2])

        # --- Formulaire de mise à jour du profil ---
        first_name = st.text_input("Prénom", value=user["first_name"])
        last_name = st.text_input("Nom", value=user["last_name"])
        num = st.text_input("Numéro", value=num_init)
        street = st.text_input("Rue", value=street_init)
        cp = st.text_input("Code postal", value=cp_init)
        city = st.text_input("Ville", value=city_init)

        if not (first_name and last_name and num and street and cp and city):
            st.error("Veuillez remplir tous les champs.")
            st.stop()

        # --- Bouton mise à jour du profil ---
        if st.button("💾 Mettre à jour le profil"):
            # Vérification des formats
            if not re.match(r"^[0-9]{1,4}[A-Za-z]?$", num.strip()):
                st.error("Numéro invalide.")
                st.stop()
            if not re.match(r"^[A-Za-zÀ-ÿ0-9'’\-\.\s]{3,}$", street.strip()):
                st.error("Rue invalide.")
                st.stop()
            if not re.match(r"^[0-9]{5}$", cp.strip()):
                st.error("Code postal invalide.")
                st.stop()
            if not re.match(r"^[A-Za-zÀ-ÿ'’\-\.\s]{2,}$", city):
                st.error("Ville invalide.")
                st.stop()

            # Envoi de la mise à jour à l’API
            address_full = f"{num.strip()} {street.strip()} {cp.strip()} {city.strip()}"
            data = {"first_name": first_name, "last_name": last_name, "address": address_full}

            r = requests.put(f"{API_URL}/users/{user['id']}", json=data)
            if r.status_code == 200:
                st.success("✅ Profil mis à jour !")
                st.session_state["users"] = requests.get(f"{API_URL}/users/{user['id']}").json()
                st.rerun()
            else:
                st.error(r.json().get("detail", "Erreur lors de la mise à jour."))

        st.divider()

        # --- Bouton déconnexion ---
        if st.button("Se déconnecter"):
            requests.delete(f"{API_URL}/users/logout", params={"token": st.session_state['token']})
            st.session_state.update({"token": None, "user_id": None, "users": None})
            st.success("Déconnexion réussie 👋")
            st.rerun()


# ======================================================
#  PAGE : ACCUEIL — Liste des produits et ajout au panier
# ======================================================
elif page == "Accueil":
    # --- Message d’accueil ---
    st.write("Bienvenue sur le site de la boutique !")
    st.subheader("🛒 Produits disponibles")

    try:
        # --- Récupération de la liste des produits via l’API ---
        resp = requests.get(f"{API_URL}/products")

        # Vérifie si la requête s’est bien passée
        if resp.status_code == 200:
            produits = resp.json()  # Récupération de la réponse JSON contenant les produits

            # --- Boucle d’affichage de chaque produit ---
            for p in produits:
                # On crée deux colonnes : infos produit à gauche, bouton/quantité à droite
                col1, col2 = st.columns([3, 1])

                # --- Colonne gauche : description du produit ---
                with col1:
                    st.markdown(f"### {p['name']}")  # Nom du produit
                    st.write(p['description'])       # Description
                    st.write(f"Prix : {p['price_cents']/100:.2f} € | Stock : {p['stock_qty']}")  # Prix + stock

                # --- Colonne droite : quantité + bouton d’ajout ---
                with col2:
                    # Sélecteur de quantité (ne peut pas dépasser le stock disponible)
                    qty = st.number_input(
                        f"Quantité pour {p['name']}",
                        min_value=1,
                        max_value=p['stock_qty'],
                        key=p['id']
                    )

                    # --- Bouton “Ajouter au panier” ---
                    if st.button(f"Ajouter au panier - {p['name']}", key="btn_" + p['id']):
                        # Vérifie que l’utilisateur est connecté
                        if not st.session_state["user_id"]:
                            st.warning("Connectez-vous pour ajouter au panier.")
                        else:
                            # Préparation des données à envoyer à l’API
                            payload = {
                                "product_id": p['id'],
                                "quantity": int(qty)
                            }

                            # --- Appel API pour ajouter un article au panier ---
                            r = requests.post(f"{API_URL}/cart/{st.session_state['user_id']}/add", json=payload)

                            # Vérification du retour de l’API
                            if r.status_code == 200:
                                st.success("Produit ajouté au panier 🛒")
                            else:
                                st.error(r.json().get("detail", "Erreur lors de l'ajout."))

        # --- Erreur API (produits non récupérés) ---
        else:
            st.error("Erreur de chargement des produits.")

    # --- Gestion des erreurs réseau ou API injoignable ---
    except Exception as e:
        st.error(f"API non disponible: {e}")

# ======================================================
#  PAGE : PANIER — Consultation, modification et commande
# ======================================================
elif page == "Panier":
    st.subheader("🧺 Votre panier")

    # --- Vérification de la connexion utilisateur ---
    if not st.session_state["user_id"]:
        st.warning("Connectez-vous d'abord.")
    else:
        user_id = st.session_state["user_id"]

        try:
            # --- Récupération du panier depuis l’API ---
            resp = requests.get(f"{API_URL}/cart/{user_id}")

            # Si l’API ne renvoie pas 200, on affiche une erreur
            if resp.status_code != 200:
                st.error(f"Erreur API ({resp.status_code})")
            else:
                panier = resp.json()

                # --- Vérification du format de la réponse ---
                # On s’assure que le panier contient bien une clé "items"
                if isinstance(panier, dict) and "items" in panier:
                    items = panier["items"]
                    # Si items est un dictionnaire, on le convertit en liste
                    if isinstance(items, dict):
                        items = list(items.values())
                else:
                    st.warning("Panier vide ou format inattendu.")
                    st.stop()

                # --- Cas où le panier est vide ---
                if not items:
                    st.info("Votre panier est vide.")
                else:
                    # --- Boucle d’affichage de chaque article dans le panier ---
                    for item in items:
                        col1, col2, col3 = st.columns([3, 1, 1])

                        # --- Colonne 1 : Informations sur le produit ---
                        with col1:
                            # Récupération des informations du produit depuis l’API
                            resp = requests.get(f"{API_URL}/products/{item['product_id']}")
                            if resp.status_code != 200:
                                st.error(f"Erreur API ({resp.status_code})")
                            else:
                                produit = resp.json()
                                st.write(f"🛍️ Produit: `{produit['name']}` | Qté: {item['quantity']}")

                        # --- Colonne 2 : Sélection de la quantité à retirer ---
                        with col2:
                            max_qty = max(1, item['quantity'])
                            qty_remove = st.number_input(
                                f"Quantité à retirer ({item['product_id']})",
                                min_value=1,
                                max_value=max_qty,
                                value=1,
                                key=f"qty_rm_{item['product_id']}"
                            )

                        # --- Colonne 3 : Bouton de suppression d’un article ---
                        with col3:
                            if st.button("❌ Retirer", key=f"rm_{item['product_id']}"):
                                # Prépare les données pour l’API de suppression
                                data = {
                                    "product_id": item["product_id"],
                                    "quantity": qty_remove
                                }

                                # --- Appel API pour retirer un article ---
                                r = requests.delete(f"{API_URL}/cart/{user_id}/remove", json=data)
                                if r.status_code == 200:
                                    st.success("Article supprimé du panier.")
                                    st.rerun()
                                else:
                                    st.error(r.json().get("detail", "Erreur lors de la suppression."))

                    # --- Affichage du total du panier ---
                    total_resp = requests.get(f"{API_URL}/cart/{user_id}/total")
                    if total_resp.status_code == 200:
                        total_json = total_resp.json()
                        if isinstance(total_json, dict) and "total_cents" in total_json:
                            st.write(f"**Total: {total_json['total_cents']/100:.2f} €**")

                    # --- Bouton : Vider tout le panier ---
                    if st.button("🗑️ Vider tout le panier"):
                        r = requests.delete(f"{API_URL}/cart/{user_id}/clear")
                        if r.status_code == 200:
                            st.success("Panier vidé.")
                            st.rerun()

                    # --- Bouton : Passer à la commande (checkout) ---
                    if st.button("✅ Passer la commande"):
                        r = requests.post(f"{API_URL}/orders/checkout/{user_id}")
                        if r.status_code == 200:
                            st.success("Commande créée avec succès !")
                            st.rerun()
                        else:
                            st.error(r.json().get("detail", "Erreur lors du checkout."))

        # --- Gestion des erreurs de communication avec l’API ---
        except Exception as e:
            st.error(f"API non disponible: {e}")

# ======================================================
#  PAGE : COMMANDES — Suivi, paiement et support client
# ======================================================
elif page == "Commandes":
    st.subheader("📦 Vos commandes")

    # --- Vérifie que l'utilisateur est connecté ---
    if not st.session_state["user_id"]:
        st.warning("Connectez-vous d'abord.")
    else:
        user_id = st.session_state["user_id"]

        try:
            # --- Récupération des commandes de l'utilisateur via l'API ---
            resp = requests.get(f"{API_URL}/orders/{user_id}")

            if resp.status_code == 200:
                commandes = resp.json()

                # Trie les commandes par date de création (plus récentes en premier)
                commandes = sorted(commandes, key=lambda c: c.get("created_at", 0), reverse=True)

                # --- Si des commandes existent ---
                if commandes:
                    for cmd in commandes:
                        st.write(f"### Commande {cmd['id']}")

                        # --- Traduction du statut numérique en texte lisible ---
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

                        # --- Liste des articles contenus dans la commande ---
                        if "items" in cmd:
                            total = 0
                            for item in cmd["items"]:
                                line_total = (item["unit_price_cents"] * item["quantity"]) / 100
                                total += line_total
                                st.markdown(f"- 🛒 `{item['name']}` × {item['quantity']} – {line_total:.2f} €")
                            st.write(f"**💰 Total : {total:.2f} €**")

                        # ------------------------------------------------------
                        #  OPTIONS DISPONIBLES : Paiement & Annulation
                        # ------------------------------------------------------
                        if status_value in ["CREE", "VALIDEE"]:
                            col1, col2 = st.columns(2)

                            # --- Colonne gauche : Paiement de la commande ---
                            with col1:
                                with st.expander("💳 Payer cette commande"):
                                    st.info("Entrez vos informations de carte pour effectuer le paiement.")

                                    # Champs de paiement
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

                                    # --- Bouton de validation du paiement ---
                                    if st.button(f"💰 Confirmer le paiement ({cmd['id']})", key=f"pay_{cmd['id']}"):
                                        now = datetime.datetime.now()
                                        current_year = now.year
                                        current_month = now.month

                                        # Vérification basique des champs carte bancaire
                                        if not card_number or not cvc or len(card_number) < 12 or len(cvc) != 3:
                                            st.warning("Veuillez saisir des informations de carte valides.")
                                        elif int(exp_year) < current_year or (int(exp_year) == current_year and int(exp_month) < current_month):
                                            st.error("❌ Cette carte est expirée. Veuillez utiliser une autre carte.")
                                        else:
                                            # Préparation des données pour le paiement
                                            pay = {
                                                "order_id": cmd["id"],
                                                "card_number": card_number.strip(),
                                                "exp_month": int(exp_month),
                                                "exp_year": int(exp_year),
                                                "cvc": cvc.strip()
                                            }

                                            # --- Appel API de paiement ---
                                            r = requests.post(f"{API_URL}/orders/pay", json=pay)
                                            if r.status_code == 200:
                                                st.session_state["just_paid"] = cmd["id"]
                                                st.success("Paiement réussi 💳")
                                                st.rerun()
                                            else:
                                                st.error(r.json().get("detail", "Erreur de paiement."))

                            # --- Colonne droite : Annulation de commande ---
                            with col2:
                                with st.expander("❌ Annuler cette commande"):
                                    st.warning("Cette action est irréversible. La commande sera annulée et les stocks remis à jour.")

                                    confirm_key = f"confirm_cancel_{cmd['id']}"
                                    if confirm_key not in st.session_state:
                                        st.session_state[confirm_key] = False

                                    # Bouton pour initier la confirmation d'annulation
                                    if st.button(f"🗑️ Annuler la commande ({cmd['id']})", key=f"cancel_{cmd['id']}"):
                                        st.session_state[confirm_key] = True

                                    # --- Double confirmation avant annulation ---
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

                        # ------------------------------------------------------
                        #  STATUTS AVANCÉS : Suivi de livraison et remboursements
                        # ------------------------------------------------------
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

                        # ------------------------------------------------------
                        #  FACTURE (Téléchargement)
                        # ------------------------------------------------------
                        if status_value in ["PAYEE", "EXPEDIEE", "LIVREE", "REMBOURSEE"]:
                            invoice_resp = requests.get(f"{API_URL}/orders/{cmd['id']}/invoice")
                            if invoice_resp.status_code == 200:
                                invoice = invoice_resp.json()

                                # --- Bouton de téléchargement de la facture ---
                                st.download_button(
                                    label="🧾 Télécharger la facture",
                                    data=json.dumps(invoice, indent=4),
                                    file_name=f"facture_{cmd['id']}.json",
                                    mime="application/json"
                                )
                            else:
                                st.warning("Facture en cours de génération…")

                        # ------------------------------------------------------
                        #  SUPPORT CLIENT (ouverture de ticket)
                        # ------------------------------------------------------
                        with st.expander("📬 Contacter le support pour cette commande"):
                            user_id = st.session_state["user_id"]
                            user_uuid = st.session_state["user_id"]

                            # Objet et message du ticket
                            default_subject = f"Problème commande {cmd['id']}"
                            subject_support = st.text_input(
                                f"Objet ticket ({cmd['id']})",
                                value=default_subject,
                                key=f"subject_{cmd['id']}"
                            )
                            msg_support = st.text_area(
                                "Expliquez votre problème :",
                                key=f"support_msg_{cmd['id']}"
                            )

                            # --- Bouton pour ouvrir un ticket support ---
                            if st.button("📨 Ouvrir un ticket support", key=f"open_ticket_{cmd['id']}"):
                                if not msg_support.strip():
                                    st.warning("Veuillez écrire un message avant d'envoyer.")
                                else:
                                    # Création du ticket (thread)
                                    thread_data = {
                                        "user_id": user_id,
                                        "order_id": cmd["id"],
                                        "subject": subject_support.strip()
                                    }
                                    r_th = requests.post(f"{API_URL}/threads/open", json=thread_data)

                                    if r_th.status_code == 200:
                                        thread = r_th.json()
                                        thread_id = thread["id"]

                                        # Envoi du premier message lié au ticket
                                        msg_data = {
                                            "thread_id": thread_id,
                                            "author_user_id": user_uuid,
                                            "body": msg_support.strip()
                                        }
                                        r_msg = requests.post(f"{API_URL}/threads/post", json=msg_data)

                                        if r_msg.status_code == 200:
                                            st.success("✅ Ticket envoyé au support !")
                                            st.rerun()
                                        else:
                                            st.error("Erreur lors de l’envoi du message.")
                                    else:
                                        st.error("Erreur lors de la création du ticket.")

                        st.write("---")

                # --- Aucun historique de commande ---
                else:
                    st.info("Aucune commande trouvée.")
            else:
                st.error("Erreur lors du chargement des commandes.")
        except Exception as e:
            st.error(f"API non disponible: {e}")

# ======================================================
#  PAGE : SUPPORT — Création et suivi des tickets client
# ======================================================
elif page == "Support":
    st.subheader("🎫 Support client")

    # --- Vérifie que l'utilisateur est connecté ---
    if not st.session_state["user_id"]:
        st.warning("Connectez-vous pour accéder au support.")
    else:
        user_id = st.session_state["user_id"]
        user_i = st.session_state["user_id"]  # Alias local (utilisé dans les messages)

        # ------------------------------------------------------
        #  SECTION 1 : Création d’un nouveau ticket support
        # ------------------------------------------------------
        st.markdown("### 📬 Créer un nouveau ticket")

        # --- Champs du formulaire de création de ticket ---
        subject = st.text_input("Objet du ticket")
        message = st.text_area("Décrivez votre problème :", placeholder="Expliquez votre situation ici...")

        # --- Bouton pour soumettre un nouveau ticket ---
        if st.button("📨 Créer le ticket"):
            # Vérification basique des champs requis
            if not subject.strip():
                st.warning("Veuillez entrer un objet de ticket.")
            elif not message.strip():
                st.warning("Veuillez écrire un message avant d’envoyer.")
            else:
                try:
                    # --- Étape 1 : Création du “thread” (discussion du ticket) ---
                    payload_thread = {
                        "user_id": user_id,   # ID de l’utilisateur qui ouvre le ticket
                        "order_id": None,     # Aucun lien direct avec une commande (ticket général)
                        "subject": subject.strip()
                    }

                    thread_resp = requests.post(f"{API_URL}/threads/open", json=payload_thread)

                    if thread_resp.status_code == 200:
                        thread = thread_resp.json()
                        thread_id = thread["id"]

                        # --- Étape 2 : Ajout du premier message au ticket ---
                        payload_message = {
                            "thread_id": thread_id,
                            "author_user_id": user_i,
                            "body": message.strip()
                        }

                        msg_resp = requests.post(f"{API_URL}/threads/post", json=payload_message)

                        # --- Confirmation de création ---
                        if msg_resp.status_code == 200:
                            st.success("✅ Ticket créé avec succès !")
                            st.rerun()
                        else:
                            st.error(msg_resp.json().get("detail", "Erreur lors de l'envoi du message."))
                    else:
                        st.error(thread_resp.json().get("detail", "Erreur lors de la création du ticket."))

                # --- Gestion des erreurs de communication avec l’API ---
                except Exception as e:
                    st.error(f"Impossible de contacter l'API : {e}")

        # ------------------------------------------------------
        #  SECTION 2 : Liste et gestion des tickets existants
        # ------------------------------------------------------
        st.divider()
        st.markdown("### 📋 Vos tickets")

        try:
            # --- Récupération de tous les tickets de l'utilisateur ---
            resp = requests.get(f"{API_URL}/threads/{user_id}")

            if resp.status_code == 200:
                threads = resp.json()

                # --- Si l’utilisateur a déjà des tickets ouverts ---
                if threads:
                    # Trie les tickets du plus récent au plus ancien
                    threads = sorted(threads, key=lambda t: t.get("created_at", 0), reverse=True)

                    # --- Boucle d’affichage de chaque ticket ---
                    for th in threads:
                        # Si le ticket est lié à une commande, on affiche l’ID
                        order_info = f" | Commande : {th['order_id']}" if th.get("order_id") else ""

                        # --- Bloc déroulant (expander) pour chaque ticket ---
                        with st.expander(f"🎟️ {th['subject']}{order_info} {'(Fermé)' if th.get('closed') else ''}"):

                            # --- Affiche la date de création du ticket ---
                            st.write(f"📅 Créé le : {datetime.datetime.fromtimestamp(th['created_at']).strftime('%d/%m/%Y %H:%M')}")
                            st.markdown("---")

                            # --- Boucle d’affichage de tous les messages du ticket ---
                            for msg in th['messages']:
                                sender = "🧑 Vous" if msg["author_user_id"] == user_i else "🎧 Support"
                                date = datetime.datetime.fromtimestamp(msg["created_at"]).strftime("%d/%m/%Y %H:%M")
                                st.markdown(f"**{sender}** ({date}) :\n> {msg['body']}")

                            # ------------------------------------------------------
                            #  Envoi de nouveaux messages (si le ticket est ouvert)
                            # ------------------------------------------------------
                            if not th.get("closed", False):
                                new_msg = st.text_area("✉️ Votre réponse :", key=f"msg_{th['id']}")

                                if st.button("Envoyer", key=f"send_{th['id']}"):
                                    if not new_msg.strip():
                                        st.warning("Votre message est vide.")
                                    else:
                                        # --- Envoi d’un nouveau message au support ---
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

                            # --- Ticket fermé : lecture seule ---
                            else:
                                st.info("🔒 Ce ticket est fermé, vous ne pouvez plus répondre.")

                # --- Aucun ticket existant ---
                else:
                    st.info("Aucun ticket trouvé.")

            # --- Erreur de récupération des tickets ---
            else:
                st.error("Erreur lors du chargement des tickets.")

        # --- Erreur de communication avec le backend ---
        except Exception as e:
            st.error(f"API non disponible : {e}")

# ======================================================
#  PAGE : ADMIN — Gestion des produits, commandes et tickets
# ======================================================
elif page == "Admin":
    st.subheader("⚙️ Administration – Gestion des produits")

    # --- Vérification des droits d’accès ---
    if not st.session_state.get("is_admin", False):
        st.warning("Accès réservé aux administrateurs.")
    else:
        # ------------------------------------------------------
        #  SECTION 1 : Création d’un nouveau produit
        # ------------------------------------------------------
        st.write("Créer un nouveau produit :")

        # --- Formulaire de création de produit ---
        name = st.text_input("Nom du produit")
        description = st.text_area("Description")
        price_cents = st.number_input("Prix (en centimes)", min_value=0, step=100)
        stock_qty = st.number_input("Quantité en stock", min_value=0, step=1)

        # Si stock nul, le produit ne peut pas être actif
        if stock_qty == 0:
            st.info("⚠️ Le produit ne peut pas être actif avec un stock nul.")
            active = st.checkbox("Produit actif", value=False, disabled=True)
        else:
            active = st.checkbox("Produit actif", value=True)

        # --- Bouton de création du produit ---
        if st.button("Créer le produit"):
            if not name or not description:
                st.warning("Veuillez remplir tous les champs.")
            else:
                payload = {
                    "name": name,
                    "description": description,
                    "price_cents": int(price_cents),
                    "stock_qty": int(stock_qty),
                    "active": active if stock_qty > 0 else False
                }

                # --- Appel API : création du produit ---
                try:
                    resp = requests.post(f"{API_URL}/products", json=payload)
                    if resp.status_code == 200:
                        st.success(f"✅ Produit '{name}' créé avec succès !")
                        st.rerun()
                    else:
                        st.error(resp.json().get("detail", "Erreur lors de la création du produit."))
                except Exception as e:
                    st.error(f"Erreur de communication avec l’API : {e}")

        st.write("---")

        # ------------------------------------------------------
        #  SECTION 2 : Liste et mise à jour des produits existants
        # ------------------------------------------------------
        st.subheader("📦 Liste des produits")

        try:
            # --- Récupération de tous les produits (actifs + inactifs) ---
            resp = requests.get(f"{API_URL}/products/all")
            if resp.status_code == 200:
                all_products = resp.json()
                if not all_products:
                    st.info("Aucun produit trouvé.")
                else:
                    # --- Affichage de chaque produit dans un expander ---
                    for prod in all_products:
                        with st.expander(f"🛍️ {prod['name']}"):
                            st.write(f"**ID :** {prod['id']}")
                            st.write(f"**Description :** {prod['description']}")
                            st.write(f"**Prix :** {prod['price_cents']/100:.2f} €")
                            st.write(f"**Statut :** {'✅ Actif' if prod['active'] else '❌ Inactif'}")

                            # Champ pour modifier le stock
                            new_stock = st.number_input(
                                f"Stock pour {prod['name']}",
                                min_value=0,
                                value=prod['stock_qty'],
                                step=1,
                                key=f"stock_{prod['id']}"
                            )

                            # Si stock > 0, le produit peut être actif
                            can_be_active = new_stock > 0
                            new_active = st.checkbox(
                                f"Produit actif ({prod['name']})",
                                value=prod['active'] and can_be_active,
                                disabled=not can_be_active,
                                key=f"active_{prod['id']}"
                            )

                            # --- Bouton pour mettre à jour le produit ---
                            if st.button(f"💾 Mettre à jour {prod['name']}", key=f"update_{prod['id']}"):
                                updated_data = {
                                    "name": prod["name"],
                                    "description": prod["description"],
                                    "price_cents": prod["price_cents"],
                                    "stock_qty": int(new_stock),
                                    "active": bool(new_active)
                                }

                                r = requests.put(f"{API_URL}/products/{prod['id']}", json=updated_data)
                                if r.status_code == 200:
                                    st.success(f"✅ Produit {prod['name']} mis à jour.")
                                    st.rerun()
                                else:
                                    st.error(r.json().get("detail", "Erreur de mise à jour."))

            else:
                st.error("Erreur lors du chargement des produits.")
        except Exception as e:
            st.error(f"API non disponible : {e}")

        st.write("---")

        # ------------------------------------------------------
        #  SECTION 3 : Gestion des commandes (côté administrateur)
        # ------------------------------------------------------
        st.subheader("📦 Gestion des commandes")

        try:
            admin_id = st.session_state["user_id"]
            resp = requests.get(f"{API_URL}/admin/orders", params={"admin_user_id": admin_id})
        except:
            st.error("Impossible de charger les commandes.")
        else:
            if resp.status_code != 200:
                st.error("Erreur lors du chargement des commandes.")
            else:
                commandes = resp.json()

                if not commandes:
                    st.info("Aucune commande.")
                else:
                    status_map = {
                        1: "CREE",
                        2: "VALIDEE",
                        3: "PAYEE",
                        4: "EXPEDIEE",
                        5: "LIVREE",
                        6: "ANNULEE",
                        7: "REMBOURSEE"
                    }

                    for cmd in commandes:
                        status_text = status_map.get(cmd["status"], "Inconnu")
                        with st.expander(f"📦 Cmd {cmd['id']} — {status_text}"):

                            # --- Liste des articles dans la commande ---
                            if "items" in cmd:
                                total = 0
                                for item in cmd["items"]:
                                    st.write(f"- `{item['name']}` × {item['quantity']}")
                                    total += (item["unit_price_cents"] * item["quantity"]) / 100
                                st.write(f"💰 Total : {total:.2f} €")
                            st.write("---")

                            # --- Actions disponibles selon le statut de la commande ---
                            if status_text == "CREE":
                                if st.button(f"✅ Valider commande {cmd['id']}", key=f"val_{cmd['id']}"):
                                    r = requests.post(
                                        f"{API_URL}/orders/validate",
                                        params={"admin_user_id": admin_id, "order_id": cmd["id"]}
                                    )
                                    st.rerun()

                            if status_text in ["VALIDEE", "PAYEE"]:
                                if st.button(f"🚚 Expédier commande {cmd['id']}", key=f"ship_{cmd['id']}"):
                                    r = requests.post(
                                        f"{API_URL}/orders/ship",
                                        params={"admin_user_id": admin_id, "order_id": cmd["id"]}
                                    )
                                    st.rerun()

                            if status_text == "EXPEDIEE":
                                if st.button(f"📬 Marquer livrée {cmd['id']}", key=f"liv_{cmd['id']}"):
                                    r = requests.post(
                                        f"{API_URL}/orders/mark_delivered",
                                        params={"admin_user_id": admin_id, "order_id": cmd["id"]}
                                    )
                                    st.rerun()

                            if status_text in ["CREE", "VALIDEE"]:
                                if st.button(f"❌ Annuler commande {cmd['id']}", key=f"cancel_admin_{cmd['id']}"):
                                    r = requests.post(
                                        f"{API_URL}/orders/admin/cancel",
                                        params={
                                            "admin_user_id": admin_id,
                                            "order_id": cmd["id"],
                                            "user_id": cmd["user_id"]
                                        }
                                    )
                                    st.rerun()

                            if status_text in ["PAYEE", "LIVREE"]:
                                if st.button(f"💸 Rembourser commande {cmd['id']}", key=f"refund_{cmd['id']}"):
                                    r = requests.post(
                                        f"{API_URL}/orders/refund",
                                        params={"admin_user_id": admin_id, "order_id": cmd["id"]}
                                    )
                                    st.rerun()

        # ------------------------------------------------------
        #  SECTION 4 : Gestion des tickets support (côté admin)
        # ------------------------------------------------------
        st.markdown("## 🎫 Gestion des tickets support")

        try:
            resp = requests.get(f"{API_URL}/admin/threads")

            if resp.status_code == 200:
                threads = resp.json()
                if threads:
                    # Tri des tickets par date (plus récents en haut)
                    threads = sorted(threads, key=lambda t: t.get("created_at", 0), reverse=True)

                    for th in threads:
                        order_info = f" | Cmd: {th['order_id']}" if th.get("order_id") else ""
                        with st.expander(f"🎟️ {th['subject']}{order_info} — Utilisateur: {th['user_id']} {'(Fermé)' if th['closed'] else ''}"):

                            st.write(f"📅 Créé le : {datetime.datetime.fromtimestamp(th['created_at']).strftime('%d/%m/%Y %H:%M')}")
                            st.markdown("---")

                            # --- Historique des messages du ticket ---
                            for msg in th["messages"]:
                                sender = "🎧 Support" if msg["author_user_id"] is None else f"🧑 {msg['author_user_id']}"
                                date = datetime.datetime.fromtimestamp(msg["created_at"]).strftime("%d/%m/%Y %H:%M")
                                st.markdown(f"**{sender}** ({date}) :\n> {msg['body']}")

                            st.markdown("---")

                            # --- Si le ticket est encore ouvert ---
                            if not th["closed"]:
                                reply = st.text_area("✉️ Réponse de l'admin :", key=f"reply_{th['id']}")
                                col1, col2 = st.columns([1, 1])

                                # --- Envoi d'une réponse admin ---
                                with col1:
                                    if st.button("📨 Envoyer", key=f"reply_btn_{th['id']}"):
                                        if not reply.strip():
                                            st.warning("Message vide.")
                                        else:
                                            payload = {
                                                "thread_id": th["id"],
                                                "author_user_id": requests.get(
                                                    f"{API_URL}/users_id/{st.session_state['user_id']}"
                                                ).json()['id'],
                                                "body": reply.strip()
                                            }

                                            r = requests.post(f"{API_URL}/threads/post", json=payload)
                                            if r.status_code == 200:
                                                st.success("Réponse envoyée ✅")
                                                st.rerun()
                                            else:
                                                st.error(r.json().get("detail", "Erreur lors de l’envoi."))

                                # --- Fermeture du ticket ---
                                with col2:
                                    if st.button("🔒 Fermer le ticket", key=f"close_{th['id']}"):
                                        admin_id = requests.get(
                                            f"{API_URL}/users_id/{st.session_state['user_id']}"
                                        ).json()['id']

                                        r = requests.post(
                                            f"{API_URL}/threads/close?thread_id={th['id']}&admin_user_id={admin_id}"
                                        )

                                        if r.status_code == 200:
                                            st.info("Ticket fermé 🏁")
                                            st.rerun()
                                        else:
                                            st.error(r.json().get("detail", "Erreur lors de la fermeture."))
                            else:
                                st.info("🔒 Ticket fermé.")
                else:
                    st.info("Aucun ticket à afficher.")
            else:
                st.error("Erreur lors du chargement des tickets (admin).")
        except Exception as e:
            st.error(f"API non disponible : {e}")
