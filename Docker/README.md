# 🛍️ Projet Shop – API & Front en Docker

Ce projet est une application **Shop** composée de deux services principaux :  
- une **API** développée avec **FastAPI**  
- une **interface frontend** développée avec **Streamlit**

Les deux services sont conteneurisés avec **Docker** et orchestrés via **Docker Compose**.

---

## 🧱 Structure du projet

- **api/** → contient le code et le Dockerfile du backend (FastAPI)  
- **front/** → contient le code et le Dockerfile du frontend (Streamlit)  
- **docker-compose.yml** → définit les services et le réseau partagé entre eux  

---

## ⚙️ Prérequis

Avant de commencer, assure-toi d’avoir installé :

- [Docker](https://docs.docker.com/get-docker/)  
- [Docker Compose](https://docs.docker.com/compose/install/)  

---

## 🚀 Lancer le projet

Depuis le dossier `Docker/`, exécute :

```bash
docker compose up --build
```

ou, selon ta version de Docker :

```bash
docker-compose up --build
```

## 🌐 Accès aux services

http://localhost:8501](http://localhost:8501)   Interface utilisateur du site marchand


## 🧹 Arrêter les conteneurs

```bash
docker compose down
```

Pour supprimer les volumes et les images associés :

```bash
docker compose down --rmi all --volumes
```