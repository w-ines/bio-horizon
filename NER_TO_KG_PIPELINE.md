# Pipeline NER → Knowledge Graph : De A à Z

> Documentation technique du pipeline d'extraction d'entités biomédicales et de génération du Knowledge Graph dans Bio-Horizon.

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Étape 1 — Recherche PubMed](#2-étape-1--recherche-pubmed)
3. [Étape 2 — Extraction NER (PubTator3)](#3-étape-2--extraction-ner-pubtator3)
4. [Étape 3 — Construction du graphe en mémoire](#4-étape-3--construction-du-graphe-en-mémoire)
5. [Étape 4 — Persistance dans Supabase](#5-étape-4--persistance-dans-supabase)
6. [Étape 5 — API de consultation](#6-étape-5--api-de-consultation)
7. [Étape 6 — Visualisation frontend](#7-étape-6--visualisation-frontend)
8. [Schéma de données](#8-schéma-de-données)
9. [Fichiers clés](#9-fichiers-clés)
10. [Limites et contraintes](#10-limites-et-contraintes)

---

## 1. Vue d'ensemble

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐
│   PubMed     │────▶│  PubTator3   │────▶│  NetworkX    │────▶│  Supabase    │────▶│ Frontend │
│  (articles)  │     │  (NER HTTP)  │     │  (graphe)    │     │  (BDD)       │     │ (React)  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘     └──────────┘
   efetch API          biocjson API         in-memory graph      kg_nodes +          force-graph
   500 art/batch       50 PMID/req          nodes + edges        kg_edges            2D viz
```

**Flux résumé** :
1. L'utilisateur lance une requête (ex: "cancer treatment")
2. PubMed History Server renvoie les PMIDs correspondants
3. Les articles sont récupérés par batch de 500
4. PubTator3 extrait les entités biomédicales de chaque PMID
5. Les entités sont ajoutées à un graphe NetworkX en mémoire
6. Le graphe est persisté dans Supabase (tables `kg_nodes` + `kg_edges`)
7. Le frontend affiche le graphe via l'API `/kg/graph`

---

## 2. Étape 1 — Recherche PubMed

**Fichier** : `core_tools/pubmed_corpus.py`

### Processus

1. **Recherche avec History Server** (`search_with_history`)
   - Envoie la requête à l'API NCBI `esearch.fcgi`
   - Reçoit un `WebEnv` + `QueryKey` (session serveur) + `count` (nombre total de résultats)
   - Exemple : `"cancer treatment"` → 510 000 résultats

2. **Récupération par batch** (`fetch_batch`)
   - Utilise `efetch.fcgi` avec `retstart` et `retmax=500`
   - Parse le XML en dictionnaires Python (titre, abstract, PMID, auteurs, etc.)
   - Rate limiting intégré (3 req/s avec API key NCBI)

### Contraintes
- **NCBI WebEnv limite** : max ~10 000 résultats par session efetch (erreur 400 au-delà)
- **PubTator3 mode** : `maxdate` auto-réglé à -30 jours pour exclure les articles trop récents (pas encore indexés par PubTator3)

### Exemple de données article
```python
{
    "pmid": "38456789",
    "title": "Novel BRAF inhibitors in melanoma treatment",
    "abstract": "We evaluated dabrafenib combined with trametinib...",
    "authors": ["Smith J", "Doe A"],
    "journal": "J Clin Oncol",
    "pub_date": "2024/01/15"
}
```

---

## 3. Étape 2 — Extraction NER (PubTator3)

**Fichier** : `ner/backends/pubtator3_backend.py`

### Qu'est-ce que PubTator3 ?

PubTator3 est un service du NCBI qui a **pré-annoté 36M+ articles PubMed** avec des modèles NLP de pointe. Au lieu de faire tourner un modèle ML localement (lent), on récupère les annotations via HTTP en ~1-2 secondes pour 100 articles.

### Processus

1. **Préparation de la requête**
   - Les PMIDs du batch sont regroupés par chunks de 50 (taille max fiable)
   - Un **PMID sentinelle** (`12068308`, article BRAF de 2002) est injecté dans chaque chunk pour éviter les erreurs 400 quand tous les PMIDs sont trop récents

2. **Appel API PubTator3**
   ```
   GET https://www.ncbi.nlm.nih.gov/research/pubtator3-api/publications/export/biocjson
   ?pmids=12068308,38456789,38456790,...
   ```
   - Retourne un JSON BioC avec les annotations pré-calculées

3. **Parsing des annotations**
   - Chaque document contient des `passages` (titre, abstract)
   - Chaque passage contient des `annotations` avec : texte, type, position, identifiants

4. **Mapping des types d'entités**
   | PubTator3 | Bio-Horizon |
   |-----------|-------------|
   | Gene      | GENE        |
   | Disease   | DISEASE     |
   | Chemical  | DRUG        |
   | Species   | SPECIES     |
   | Mutation  | MUTATION    |
   | CellLine  | CELLLINE    |

5. **Construction du NerResult**
   ```python
   NerResult(
       entities={
           "DISEASE": [NerEntity(text="melanoma", confidence=0.95), ...],
           "DRUG": [NerEntity(text="dabrafenib", confidence=0.92), ...],
           "GENE": [NerEntity(text="BRAF", confidence=0.99), ...]
       },
       provider="pubtator3"
   )
   ```

### Normalisation des entités

**Fichier** : `kg/normalize.py`

Chaque texte d'entité est normalisé :
1. Décomposition Unicode NFKD + suppression des accents
2. Passage en minuscules
3. Compression des espaces multiples
4. Suppression de la ponctuation aux extrémités

```
"  Myocardial   Infarction " → "myocardial infarction"
"COVID-19"                    → "covid-19"
"BRCA1 "                     → "brca1"
```

L'identifiant unique d'un noeud est : `TYPE::label_normalisé`
```
"DISEASE::melanoma"
"DRUG::dabrafenib"
"GENE::braf"
```

---

## 4. Étape 3 — Construction du graphe en mémoire

**Fichier** : `kg/build.py`

### Structure du graphe

Le graphe est un **`networkx.Graph`** (non-dirigé) où :
- **Noeuds** = entités biomédicales uniques
- **Arêtes** = co-occurrences entre entités mentionnées dans le même article

### Algorithme (`add_ner_result_to_graph`)

Pour chaque article (NerResult) :

```
Article PMID:38456789 → entités: {melanoma, dabrafenib, BRAF, trametinib}

1. Pour chaque entité :
   - Si le noeud existe déjà → incrémenter frequency, ajouter le PMID aux sources
   - Sinon → créer le noeud (label, type, frequency=1, sources=[pmid])

2. Créer des arêtes de co-occurrence entre TOUTES les paires d'entités :
   melanoma ↔ dabrafenib    (même article)
   melanoma ↔ BRAF          (même article)
   melanoma ↔ trametinib    (même article)
   dabrafenib ↔ BRAF        (même article)
   dabrafenib ↔ trametinib  (même article)
   BRAF ↔ trametinib        (même article)
   
   Si l'arête existe déjà → incrémenter weight + ajouter PMID aux sources
```

### Attributs des noeuds

| Attribut         | Type           | Description                                    |
|------------------|----------------|------------------------------------------------|
| `id`             | `str`          | `"TYPE::label"` — identifiant unique           |
| `label`          | `str`          | Texte normalisé de l'entité                    |
| `entity_type`    | `str`          | `DISEASE`, `DRUG`, `GENE`, `SPECIES`, etc.     |
| `frequency`      | `int`          | Nombre d'articles mentionnant cette entité     |
| `sources`        | `List[str]`    | Liste des PMIDs sources                         |
| `confidence_max` | `Optional[float]` | Score de confiance maximum (du NER)         |

### Attributs des arêtes

| Attribut        | Type        | Description                                      |
|-----------------|-------------|--------------------------------------------------|
| `weight`        | `int`       | Nombre d'articles où les 2 entités co-occurrent  |
| `relation_type` | `str`       | Toujours `"co_occurrence"` actuellement          |
| `sources`       | `List[str]` | Liste des PMIDs où la co-occurrence est trouvée   |

### Croissance du graphe (exemple réel)

```
Batch 1  (500 articles) → ~4000 entités →  8 000 noeuds,  40 000 arêtes
Batch 5  (2500 articles) →                 15 000 noeuds, 200 000 arêtes
Batch 10 (5000 articles) →                 20 000 noeuds, 340 000 arêtes
Batch 20 (10000 articles) →                25 000 noeuds, 380 000 arêtes
```

Le nombre de noeuds plafonne (les mêmes entités reviennent), mais les arêtes croissent plus vite à cause des combinaisons.

---

## 5. Étape 4 — Persistance dans Supabase

**Fichiers** :
- `kg/store.py` — logique de persist/load
- `storage/kg_repository.py` — appels Supabase
- `migrations/kg_tables.sql` — schéma SQL

### Tables SQL

#### `kg_nodes` — une ligne = une entité unique

```sql
CREATE TABLE kg_nodes (
    id              TEXT PRIMARY KEY,           -- "DRUG::aspirin"
    label           TEXT NOT NULL,              -- "aspirin"
    entity_type     TEXT NOT NULL,              -- "DRUG"
    frequency       INT  NOT NULL DEFAULT 1,
    sources         TEXT[] NOT NULL DEFAULT '{}', -- ["38456789", "38456790"]
    confidence_max  FLOAT,
    metadata        JSONB NOT NULL DEFAULT '{}',
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### `kg_edges` — une ligne = une co-occurrence

```sql
CREATE TABLE kg_edges (
    source_id       TEXT NOT NULL REFERENCES kg_nodes(id),
    target_id       TEXT NOT NULL REFERENCES kg_nodes(id),
    weight          INT  NOT NULL DEFAULT 1,
    relation_type   TEXT NOT NULL DEFAULT 'co_occurrence',
    sources         TEXT[] NOT NULL DEFAULT '{}',
    metadata        JSONB NOT NULL DEFAULT '{}',
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (source_id, target_id)
);
```

### Processus de persistance (`persist_graph`)

1. Convertir le graphe NetworkX en `KgSnapshot` (listes de `KgNode` + `KgEdge`)
2. Upsert les noeuds par chunks de 500 (`ON CONFLICT id` → remplace)
3. Upsert les arêtes par chunks de 500 (`ON CONFLICT source_id,target_id` → remplace)
4. Mettre à jour le cache Redis

### Stratégie de persistance (optimisée)

| Événement           | Action                                           |
|---------------------|--------------------------------------------------|
| Chaque batch NER    | Ajout en mémoire seulement (rapide, ~0.1s)       |
| Tous les 20 batchs  | Checkpoint : persist vers Supabase                |
| Fin du job          | Persist finale vers Supabase                      |
| Crash/erreur        | Emergency persist (sauvegarde avant perte)        |

### Chargement au démarrage (`load_graph`)

1. Tente de lire depuis le cache Redis (rapide)
2. Si cache miss → lit depuis Supabase (`fetch_all_nodes` + `fetch_all_edges`)
3. Reconstruit le graphe NetworkX en mémoire
4. Met en cache Redis pour les prochaines lectures

---

## 6. Étape 5 — API de consultation

**Fichier** : `api/routes/kg.py`

### Endpoints

| Endpoint               | Description                                    |
|------------------------|------------------------------------------------|
| `GET /kg/graph`        | Graphe complet (filtré) en format node-link     |
| `GET /kg/stats`        | Statistiques (nb noeuds, nb arêtes)            |
| `GET /kg/node/{id}`    | Détails d'un noeud + ses voisins               |
| `GET /kg/top-nodes`    | Top N noeuds par fréquence ou degré            |

### `GET /kg/graph` — Paramètres

| Paramètre       | Type  | Défaut | Description                            |
|------------------|-------|--------|----------------------------------------|
| `entity_type`    | `str` | `null` | Filtre par type (DRUG, DISEASE, etc.)  |
| `max_nodes`      | `int` | `100`  | Nombre max de noeuds retournés         |
| `min_frequency`  | `int` | `1`    | Fréquence minimale pour inclure un noeud |

### Algorithme de filtrage

1. Filtrer par `entity_type` si spécifié
2. Filtrer les noeuds avec `frequency < min_frequency`
3. Trier par fréquence décroissante, garder les `max_nodes` premiers
4. Extraire le sous-graphe induit (noeuds + arêtes entre eux)
5. Convertir en JSON `{ nodes: [...], links: [...] }`

### Exemple de réponse

```json
{
  "nodes": [
    {"id": "DISEASE::melanoma", "label": "melanoma", "type": "DISEASE", "frequency": 342, "degree": 87},
    {"id": "DRUG::dabrafenib", "label": "dabrafenib", "type": "DRUG", "frequency": 156, "degree": 43},
    {"id": "GENE::braf", "label": "braf", "type": "GENE", "frequency": 289, "degree": 92}
  ],
  "links": [
    {"source": "DISEASE::melanoma", "target": "DRUG::dabrafenib", "weight": 98, "relation_type": "co_occurrence"},
    {"source": "DISEASE::melanoma", "target": "GENE::braf", "weight": 201, "relation_type": "co_occurrence"}
  ],
  "stats": {"total_nodes": 3, "total_edges": 2, "filtered": false}
}
```

---

## 7. Étape 6 — Visualisation frontend

**Fichier** : `ui-biomed-rag/src/components/KnowledgeGraphViewer.tsx`

### Technologie

- **react-force-graph-2d** : simulation physique force-directed (d3-force)
- Le composant React appelle `GET /kg/graph?max_nodes=100&min_frequency=1`
- Chaque noeud est coloré selon son `entity_type`
- La taille des noeuds est proportionnelle à leur `frequency`
- L'épaisseur des liens est proportionnelle au `weight`

### Couleurs par type d'entité

| Type     | Couleur  |
|----------|----------|
| DISEASE  | Rouge    |
| DRUG     | Bleu     |
| GENE     | Vert     |
| SPECIES  | Orange   |
| MUTATION | Violet   |
| CELLLINE | Gris     |

### Interactions

- **Hover** : affiche le label et la fréquence du noeud
- **Click** : met en surbrillance le noeud et ses voisins
- **Zoom/Pan** : navigation dans le graphe
- **Filtres** : par type d'entité, fréquence minimum

---

## 8. Schéma de données

### Cycle de vie d'une entité

```
PubMed Article (PMID:38456789)
    │
    ▼
PubTator3 Annotation
    │  text: "dabrafenib"
    │  type: "Chemical"
    │  confidence: 0.92
    │
    ▼
NerEntity
    │  text: "dabrafenib"
    │  confidence: 0.92
    │  label: "DRUG"
    │
    ▼
Normalisation
    │  normalize("dabrafenib") → "dabrafenib"
    │  make_node_id("DRUG", "dabrafenib") → "DRUG::dabrafenib"
    │
    ▼
NetworkX Node
    │  id: "DRUG::dabrafenib"
    │  label: "dabrafenib"
    │  entity_type: "DRUG"
    │  frequency: 156
    │  sources: ["38456789", "38456790", ...]
    │
    ▼
Supabase Row (kg_nodes)
    │  id: "DRUG::dabrafenib"
    │  label: "dabrafenib"
    │  ...
    │
    ▼
JSON API → Frontend (noeud dans le graphe visuel)
```

### Les 3 couches de stockage

| Couche        | Technologie  | Rôle                        | Durée de vie         |
|---------------|-------------|-----------------------------|-----------------------|
| **Mémoire**   | NetworkX    | Graphe actif pour l'API     | Jusqu'au restart      |
| **Cache**      | Redis       | Accélère le chargement      | TTL configurable      |
| **Persistant** | Supabase    | Stockage durable            | Permanent             |

---

## 9. Fichiers clés

| Fichier                                    | Rôle                                            |
|--------------------------------------------|-------------------------------------------------|
| `jobs/worker.py`                           | Orchestration : batch fetch → NER → KG → persist |
| `core_tools/pubmed_corpus.py`              | Client API PubMed (esearch + efetch)             |
| `ner/router.py`                            | Routeur NER (sélection du provider)              |
| `ner/backends/pubtator3_backend.py`        | Backend PubTator3 (appel HTTP + parsing BioC)    |
| `ner/schemas.py`                           | Dataclasses `NerEntity`, `NerResult`             |
| `kg/build.py`                              | Construction du graphe NetworkX                  |
| `kg/normalize.py`                          | Normalisation des labels d'entités               |
| `kg/schemas.py`                            | Dataclasses `KgNode`, `KgEdge`, `KgSnapshot`     |
| `kg/store.py`                              | Persist/Load graphe (Supabase + Redis)           |
| `storage/kg_repository.py`                 | CRUD Supabase pour kg_nodes / kg_edges           |
| `storage/kg_cache_redis.py`                | Cache Redis du graphe                            |
| `migrations/kg_tables.sql`                 | Schéma SQL des tables kg_nodes + kg_edges        |
| `api/routes/kg.py`                         | Endpoints REST `/kg/graph`, `/kg/stats`, etc.    |
| `core_tools/kg_tool.py`                    | Graphe global en mémoire (`get_graph()`)         |
| `ui-biomed-rag/.../KnowledgeGraphViewer.tsx`| Composant React de visualisation                |

---

## 10. Limites et contraintes

| Contrainte                          | Valeur         | Raison                                         |
|-------------------------------------|----------------|-------------------------------------------------|
| NCBI WebEnv max résultats           | 10 000         | API efetch retourne 400 au-delà                 |
| PubTator3 batch size                | 50 PMIDs       | Fiabilité de l'API (>100 peut timeout)          |
| PubTator3 indexation                | ~30 jours      | Articles récents pas encore annotés              |
| Supabase upsert chunk               | 500 rows       | Éviter les timeouts HTTP                         |
| max_nodes API                        | 100 (défaut)   | Performance du rendu frontend                   |
| Persist KG                           | Tous les 20 batchs | Balance vitesse vs sécurité données         |
| Articles par batch (efetch)          | 500            | Taille optimale pour le pipeline                |
| Sentinelle PMID                      | `12068308`     | Évite 400 quand tous les PMIDs sont récents     |

---

## Diagramme de séquence complet

```
Utilisateur          Frontend        Backend API        Worker           PubMed        PubTator3       Supabase
    │                   │                │                │                │               │               │
    │  "cancer treatment"                │                │                │               │               │
    │──────────────────▶│                │                │                │               │               │
    │                   │ POST /jobs     │                │                │               │               │
    │                   │───────────────▶│                │                │               │               │
    │                   │                │  create job    │                │               │               │
    │                   │                │───────────────▶│                │               │               │
    │                   │                │                │                │               │               │
    │                   │                │                │  esearch       │               │               │
    │                   │                │                │───────────────▶│               │               │
    │                   │                │                │  WebEnv+510K   │               │               │
    │                   │                │                │◀───────────────│               │               │
    │                   │                │                │                │               │               │
    │                   │                │                │ ┌─── Pour chaque batch (×20) ──────────┐      │
    │                   │                │                │ │                                       │      │
    │                   │                │                │ │ efetch 500    │               │       │      │
    │                   │                │                │ │──────────────▶│               │       │      │
    │                   │                │                │ │ articles XML  │               │       │      │
    │                   │                │                │ │◀──────────────│               │       │      │
    │                   │                │                │ │                               │       │      │
    │                   │                │                │ │ GET biocjson (50 PMIDs ×10)   │       │      │
    │                   │                │                │ │──────────────────────────────▶│       │      │
    │                   │                │                │ │ annotations NER               │       │      │
    │                   │                │                │ │◀──────────────────────────────│       │      │
    │                   │                │                │ │                                       │      │
    │                   │                │                │ │ add_ner_results_batch(graph)          │      │
    │                   │                │                │ │ (in-memory NetworkX)                  │      │
    │                   │                │                │ │                                       │      │
    │                   │                │                │ └───────────────────────────────────────┘      │
    │                   │                │                │                                                │
    │                   │                │                │  persist_graph (1× final)                      │
    │                   │                │                │───────────────────────────────────────────────▶│
    │                   │                │                │  upsert kg_nodes + kg_edges                    │
    │                   │                │                │◀───────────────────────────────────────────────│
    │                   │                │                │                                                │
    │                   │ GET /kg/graph  │                │                │               │               │
    │                   │───────────────▶│                │                │               │               │
    │                   │                │ get_graph()    │                │               │               │
    │                   │                │ (in-memory)    │                │               │               │
    │                   │  JSON nodes+links              │                │               │               │
    │                   │◀───────────────│                │                │               │               │
    │  graphe visuel    │                │                │                │               │               │
    │◀──────────────────│                │                │                │               │               │
```
