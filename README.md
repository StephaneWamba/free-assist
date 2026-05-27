# FreeAssist

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-gpt--4o--mini-412991?logo=openai&logoColor=white)
![Fly.io](https://img.shields.io/badge/Fly.io-deployed-8B5CF6?logo=fly.io&logoColor=white)
![Vercel](https://img.shields.io/badge/Vercel-deployed-black?logo=vercel&logoColor=white)
![MLflow](https://img.shields.io/badge/MLflow-tracking-0194E2?logo=mlflow&logoColor=white)

Assistant de support client pour Free (Iliad), conçu pour l'équipe DataX. Classifie les intentions, récupère le contexte via RAG, et génère des réponses avec l'API OpenAI. Inclut un pipeline ML complet pour le fine-tuning et l'évaluation d'un classifieur d'intentions basé sur CamemBERT.

![Dashboard](https://raw.githubusercontent.com/StephaneWamba/free-assist/master/images/screenshot-dashboard.png)

## Architecture

![Architecture système](https://raw.githubusercontent.com/StephaneWamba/free-assist/master/images/diagram-system-architecture.png)

Trois couches d'exécution :

- **Frontend** (Vercel) : Next.js 15 avec mises à jour temps réel via WebSocket et dashboard de monitoring
- **API** (Fly.io, Paris CDG) : FastAPI gérant la classification d'intention, la récupération RAG et la génération de réponses
- **Inférence** (optionnel, Vast.ai) : noeud GPU pour servir les modèles localement ; bascule sur OpenAI si indisponible

## Flux de requête

![Flux de requête](https://raw.githubusercontent.com/StephaneWamba/free-assist/master/images/diagram-request-flow.png)

Chaque message de support passe par :

1. Classifieur d'intentions CamemBERT (connectivité box, facturation, résiliation, etc.)
2. LangChain + FAISS récupère les chunks pertinents de la base de connaissances
3. OpenAI API (gpt-4o-mini uniquement) génère la réponse
4. Score de confiance et réponse persistés dans SQLite sur le volume Fly.io

## Infrastructure

![Déploiement et infrastructure](https://raw.githubusercontent.com/StephaneWamba/free-assist/master/images/diagram-deployment-infrastructure.png)

## Pipeline ML

![Pipeline ML](https://raw.githubusercontent.com/StephaneWamba/free-assist/master/images/diagram-ml-pipeline.png)

Cinq étapes :

1. **Données** - Génération de tickets synthétiques avec scripts d'augmentation
2. **Entraînement** - Fine-tuning CamemBERT avec QLoRA (PEFT) pour les setups low-VRAM
3. **Évaluation** - Accuracy, F1, matrice de confusion, loggés dans MLflow
4. **Indexation RAG** - Index FAISS construit à partir des fichiers markdown de la base de connaissances
5. **Serving** - Modèle exporté servi via un script d'inférence sur noeud GPU

## Structure

```
free-assist/
├── apps/
│   ├── api/          # Backend FastAPI
│   └── web/          # Frontend Next.js
├── ml/
│   ├── training/     # Fine-tuning CamemBERT, QLoRA
│   ├── rag/          # Indexeur FAISS et pipeline de récupération
│   ├── evaluation/   # Métriques et logging MLflow
│   └── utils/        # Préprocessing, helpers MLflow
├── data/
│   ├── knowledge_base/   # Procédures et FAQ en markdown
│   └── simulator/        # Générateur de tickets synthétiques
└── images/               # Diagrammes d'architecture et captures d'écran
```

## Installation

**Prérequis :** Python 3.11, Node.js 20, flyctl, Vercel CLI

```bash
# API
cd apps/api
cp .env.example .env   # renseigner OPENAI_API_KEY
pip install -e ".[dev]"
uvicorn app.main:app --reload

# Frontend
cd apps/web
cp .env.example .env.local   # renseigner NEXT_PUBLIC_API_URL
npm install
npm run dev
```

Pour entraîner les modèles :

```bash
cd ml
pip install -r requirements.txt
python -m data.simulator.generate          # données synthétiques
python -m ml.training.train_intent_classifier
python -m ml.rag.indexer                   # index FAISS
python -m ml.evaluation.evaluate_pipeline
```

## Déploiement

```bash
# API (depuis la racine du repo)
flyctl deploy --config apps/api/fly.toml --ha=false

# Frontend
vercel --prod
```

## Variables d'environnement

| Variable | Où | Description |
|----------|----|-------------|
| `OPENAI_API_KEY` | API | Requis pour la génération (gpt-4o-mini) |
| `HUGGINGFACE_TOKEN` | API | Pour télécharger CamemBERT |
| `INFERENCE_URL` | API (optionnel) | Endpoint du serveur d'inférence sur noeud GPU (Vast.ai) |
| `NEXT_PUBLIC_API_URL` | Web | URL de base FastAPI |
| `NEXT_PUBLIC_WS_URL` | Web | URL WebSocket |
