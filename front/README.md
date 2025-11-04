# 🛍️ Shop Frontend – Application Streamlit

Ce projet constitue l’interface utilisateur du site e-commerce.  
Il communique avec l’API **FastAPI** située sur :

[http://localhost:8000](http://localhost:8000)


L’objectif est de permettre aux utilisateurs de :

✅ Créer un compte / Se connecter  
✅ Consulter et modifier leur profil  
✅ Parcourir les produits disponibles  
✅ Gérer leur panier et commander  
✅ Suivre l’état des commandes  
✅ Contacter le support via un système de tickets  
✅ Accès administrateur : gestion produits + commandes + tickets

---

## 📌 Technologies

| Technologie | Utilisation |
|------------|-------------|
| Python 3.10+ | Langage principal |
| Streamlit | UI Web |
| Requests | Communication API |
| streamlit-option-menu | Barre de navigation |

---

## 🚀 Lancer le frontend

Assurez-vous que l’API est déjà en cours d’exécution ✅  
Dans un terminal, dans le dossier du frontend :

```bash
pip install -r requirements.txt
streamlit run frontend.py
```