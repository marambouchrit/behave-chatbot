\# BeHave AI Assistant



Assistant conversationnel RAG (Retrieval-Augmented Generation) pour la suite

logicielle BeHave (Predictive, Access, Master Data, Analytics) — développé

dans le cadre d'un stage d'ingénieur chez Siryos, Département Data Science.



L'assistant répond aux questions des utilisateurs en s'appuyant sur la

documentation officielle BeHave (guides PDF/DOCX indexés) et sur les fichiers

que l'utilisateur joint directement dans une conversation (mini-RAG isolé par

chat).



\## Stack technique



| Composant | Technologie |

|---|---|

| Backend | FastAPI, SQLAlchemy, PostgreSQL |

| Frontend | React, Vite, Tailwind CSS |

| Base vectorielle | ChromaDB |

| Embeddings | SentenceTransformers (`all-MiniLM-L6-v2`) |

| LLM | Groq API (`openai/gpt-oss-20b`) |

| Authentification | JWT (HS256) |



\## Structure du projet



```

behave-chatbot/

├── backend/              # API FastAPI

│   ├── main.py           # Point d'entrée, routes principales

│   ├── core/              # Sécurité JWT, dépendances FastAPI

│   ├── database/          # Modèles SQLAlchemy, opérations CRUD

│   ├── routers/            # Routes auth et administration documentaire

│   ├── schemas/            # Schémas Pydantic

│   └── services/            # Traitement des fichiers uploadés, service documentaire

├── rag/                   # Pipeline RAG (retrieval, orchestration, prompts)

│   ├── chain.py

│   ├── retriever.py

│   └── prompt\_builder.py

├── ingestion/             # Ingestion et indexation de la documentation BeHave

│   ├── run\_indexation.py

│   ├── document\_loader.py

│   ├── chunker.py

│   └── embedder.py

├── frontend/               # Application React

│   └── src/

│       ├── components/      # Chat, upload de fichiers, admin

│       ├── pages/            # Login, Register, pages admin

│       └── services/          # Appels API (auth, chat, admin)

├── data/

│   ├── documents/            # Documentation BeHave source (non versionné)

│   └── chroma\_db/             # Base vectorielle persistante (non versionné)

└── requirements.txt

```



\## Prérequis



\- Python 3.12

\- Node.js 18+

\- PostgreSQL (instance locale ou distante)

\- Une clé API Groq (https://console.groq.com)



\## Installation



\### 1. Backend



```powershell

python -m venv venv

venv\\Scripts\\activate

pip install -r requirements.txt

```



Copiez `.env.example` vers `.env` à la racine du projet et renseignez les

valeurs :



```powershell

Copy-Item .env.example .env

```



Variables à configurer dans `.env` :



| Variable | Description |

|---|---|

| `ADMIN\_USERNAME` | Nom d'utilisateur du compte administrateur créé au démarrage |

| `ADMIN\_PASSWORD\_HASH` | Hash bcrypt du mot de passe admin (voir `backend/generate\_admin\_hash.py`) |

| `JWT\_SECRET\_KEY` | Clé secrète de signature des tokens JWT |

| `DATABASE\_URL` | Chaîne de connexion PostgreSQL |

| `GROQ\_API\_KEY` | Clé API Groq |

| `CHROMA\_DB\_DIR` | Chemin absolu vers le dossier de persistance ChromaDB |



Pour générer un hash de mot de passe admin :



```powershell

python backend\\generate\_admin\_hash.py

```



\### 2. Indexation de la documentation BeHave



Placez les guides PDF/DOCX dans `data/documents/`, puis lancez :



```powershell

python ingestion\\run\_indexation.py

```



Ce script découpe les documents en chunks, génère leurs embeddings et les

indexe dans ChromaDB. Un test de fumée est exécuté automatiquement en fin de

script pour vérifier que l'indexation est cohérente.



\### 3. Démarrage du backend



```powershell

cd backend

uvicorn main:app --reload

```



L'API est accessible sur `http://127.0.0.1:8000`, avec documentation

interactive Swagger sur `http://127.0.0.1:8000/docs`.



\### 4. Frontend



```powershell

cd frontend

npm install

Copy-Item .env.example .env

npm run dev

```



L'application est accessible sur `http://127.0.0.1:5173` (ou le port indiqué

par Vite).



\## Fonctionnalités principales



\- \*\*Pipeline RAG\*\* sur la documentation officielle BeHave, avec détection

&#x20; automatique du module concerné (Predictive, Access, Master Data, Analytics)

&#x20; à partir des métadonnées ChromaDB.

\- \*\*Mini-RAG pour fichiers joints\*\* : les documents PDF/DOCX uploadés par

&#x20; l'utilisateur sont indexés dans une collection ChromaDB isolée par

&#x20; conversation. À chaque question, l'assistant compare la pertinence de la

&#x20; documentation officielle et des fichiers joints, et sélectionne

&#x20; automatiquement la source la plus pertinente.

\- \*\*Conversations multiples\*\* par utilisateur, avec auto-renommage à la

&#x20; première question.

\- \*\*Interface d'administration\*\* : gestion de la base documentaire, historique

&#x20; des conversations de tous les utilisateurs.

\- \*\*Authentification JWT\*\* avec rôles utilisateur/administrateur.

\- \*\*Dictée vocale\*\* (Web Speech API) et support multilingue.







\## Auteure



Maram Bouchrit — stage d'ingénieur, ENICarthage / Siryos, Été 2026.

