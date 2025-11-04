# 🛍️ Shop API

API REST pour une boutique en ligne : gestion des utilisateurs, produits, paniers,
commandes, paiements, factures et support client.

✅ Basée sur FastAPI  
✅ Stockage in-memory (pas de base de données)  
✅ Documentation OpenAPI / Swagger incluse  
✅ Gestion d’un workflow E-Commerce complet

---

## 🚀 Lancer l’API en local

```bash
pip install -r requirements.txt
fastapi dev api-shop.py
```

## 📌 L’API est disponible sur :

- Swagger UI → [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc → [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- Health check → [http://127.0.0.1:8000/status](http://127.0.0.1:8000/status)

## Documentation du fichier métier

```bash
pdoc ./shop.py
```

ouvre une feunetre dans le navigateur avec la documentation

### pour avoir un rapport sur la couverture de test:

```bash
pytest api/tests --cov=api.shop --cov-report=term --cov-report=html
```