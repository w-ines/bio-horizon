# BioHorizon — Détection de Signaux Émergents dans la Littérature Biomédicale

**Version** : 1.0  
**Date** : Mars 2026  
**Statut** : Spécification initiale

---

## Table des matières

1. [Problématique](#1-problématique)
2. [Proposition de valeur](#2-proposition-de-valeur)
3. [Objectifs](#3-objectifs)
4. [Public cible](#4-public-cible)
5. [Concepts clés](#5-concepts-clés)
6. [Architecture fonctionnelle](#6-architecture-fonctionnelle)
7. [Architecture technique](#7-architecture-technique)
8. [Arborescence du projet](#8-arborescence-du-projet)
9. [Fonctionnalités détaillées](#9-fonctionnalités-détaillées)
10. [Stack technologique](#10-stack-technologique)
11. [Modèle de données](#11-modèle-de-données)
12. [Roadmap](#12-roadmap)
13. [Positionnement et différenciation](#13-positionnement-et-différenciation)
14. [Risques et mitigations](#14-risques-et-mitigations)
15. [Interopérabilité LinkRdata / LinkRbrain](#15-interopérabilité-linkrdata--linkrbrain)

---

## 1. Problématique

### Le constat

La recherche biomédicale produit un volume massif et croissant de publications. PubMed indexe plus de **36 millions d'articles** et en ajoute plusieurs milliers chaque jour. Aucun chercheur, aucune équipe ne peut absorber ce flux.

### Les limites des outils actuels

| Outil | Ce qu'il fait | Ce qu'il ne fait pas |
|-------|--------------|---------------------|
| **Alertes PubMed** | Envoie les nouveaux articles par email | Ne détecte pas de tendances, ne structure rien |
| **Gargantext** | Carte statique de cooccurrences sur un corpus | Ne compare pas dans le temps, pas de NER médical spécialisé |
| **BioKGrapher** | Construit un KG à partir de PMIDs | Pas de dimension temporelle, pas de détection d'émergence |
| **PubMed KG 2.0** | KG massif (papers, patents, trials) | Dataset statique, pas d'outil de veille dynamique |

### Le problème fondamental

**Personne ne détecte ce qui est en train de changer.**

Les outils existants répondent à la question "Que sait-on sur X ?" mais pas à la question bien plus stratégique : **"Qu'est-ce qui est en train d'émerger autour de X ?"**

Quand 3 équipes indépendantes commencent à publier sur une association inattendue (ex : un médicament anti-diabétique lié à l'Alzheimer), ce signal est invisible pour un chercheur qui lit ses articles un par un. Il ne devient visible que si l'on observe l'**évolution du paysage scientifique dans le temps**.

### Enjeux

- **Pour les chercheurs** : manquer un signal émergent, c'est perdre des mois de positionnement
- **Pour les biotechs** : détecter une tendance trop tard, c'est rater une opportunité stratégique
- **Pour les cliniciens** : ne pas suivre l'évolution des connaissances, c'est risquer l'obsolescence

---

## 2. Proposition de valeur

### En une phrase

> **BioHorizon est un système de détection de signaux émergents dans la littérature biomédicale. Il utilise OpenMed pour extraire des entités médicales (NER), qualifier leur statut (assertion), et permettre des entités custom (zero-shot). Il construit un Knowledge Graph temporel qui détecte non seulement ce qui émerge, mais aussi le NIVEAU DE CONSENSUS de la communauté scientifique sur chaque association. Les données structurées peuvent alimenter des plateformes comme LinkRdata/LinkRbrain.**

### Avant BioHorizon

- Le chercheur reçoit 50-100 alertes email/semaine → bruit
- Il passe 2-3h à trier manuellement → perte de temps
- Il rate les signaux émergents → risque stratégique
- Il n'a aucune vue temporelle → pas de recul

### Après BioHorizon

- Un rapport hebdomadaire structuré avec **signaux émergents** classés par score
- Un **Knowledge Graph temporel** qui montre l'évolution du paysage scientifique
- Des **alertes automatiques** quand un nouveau pont apparaît entre deux domaines
- Un **avantage temporel** de 4 à 12 semaines sur la veille manuelle
- Un **score de consensus** par association : la communauté est-elle d'accord ? (positif/négatif/hypothétique)
- Des **entités custom** configurables par l'utilisateur via Zero-shot NER (sans re-entraînement)
- Un **export structuré** compatible avec LinkRdata/LinkRbrain pour enrichir les graphes neurosciences

---

## 3. Objectifs

### 3.1 Objectif principal

Construire un système de **détection précoce de l'évolution des connaissances biomédicales**, basé sur l'analyse temporelle d'un Knowledge Graph enrichi par NER médical (OpenMed), qualification d'assertions, et NER zero-shot configurable. Le système mesure le **niveau de consensus scientifique** pour chaque signal émergent et produit des données structurées interopérables avec des plateformes comme LinkRdata/LinkRbrain.

### 3.2 Objectifs spécifiques

#### Court terme (MVP — 4 semaines)

- [ ] Interroger PubMed en temps réel avec filtres avancés
- [ ] Extraire les entités médicales (maladies, médicaments, gènes) avec OpenMed
- [ ] Construire un Knowledge Graph de cooccurrences à partir des entités extraites
- [ ] Stocker des snapshots temporels du KG (hebdomadaires)
- [ ] Calculer un score d'émergence pour chaque entité et relation
- [ ] Afficher un dashboard avec les signaux émergents

#### Moyen terme (8-12 semaines)

- [ ] Comparaison visuelle de KG entre deux périodes
- [ ] Alertes automatiques (email/webhook) sur signaux forts
- [ ] RAG conversationnel sourcé avec citations PMIDs
- [ ] Requêtes de veille sauvegardées avec exécution périodique
- [ ] Export des rapports (PDF, JSON)
- [ ] **OpenMed Assertion Status** : qualifier chaque entité (présent/absent/hypothétique/passé)
- [ ] **Score de consensus** : % positif/négatif/hypothétique par relation
- [ ] **Zero-shot NER** : entités custom configurables par l'utilisateur (ex: BRAIN_REGION, BIOMARKER)

#### Long terme (6+ mois)

- [ ] Détection de contradictions dans la littérature (basée sur Assertion Status)
- [ ] Comparaison multi-pathologies (drug repurposing)
- [ ] Intégration de ClinicalTrials.gov et brevets
- [ ] API publique pour intégration dans d'autres outils
- [ ] **Export LinkRdata** : entités + relations structurées pour alimenter LinkRbrain
- [ ] **PII/Dé-identification** (OpenMed) : anonymisation HIPAA/RGPD si données patients

---

## 4. Public cible

### Persona 1 : Chercheur / Doctorant

- **Besoin** : Suivre 2-5 sujets, détecter les nouvelles directions de recherche
- **Fréquence** : Consultation hebdomadaire
- **Valeur** : Économise 5-10h/semaine, ne rate plus de signal émergent
- **Exemple** : Doctorant travaillant sur la résistance aux antibiotiques — détecte l'émergence d'un nouveau mécanisme de résistance 6 semaines avant ses collègues

### Persona 2 : Startup biotech / Pharma

- **Besoin** : Veille concurrentielle, détection d'opportunités
- **Fréquence** : Consultation quotidienne
- **Valeur** : Anticipe les tendances, identifie les opportunités de repositionnement
- **Exemple** : Startup en thérapie génique — détecte que 3 équipes convergent vers un nouveau vecteur AAV, ajuste sa stratégie R&D

### Persona 3 : Médecin-chercheur

- **Besoin** : Rester à jour malgré la charge clinique
- **Fréquence** : Consultation hebdomadaire (digest)
- **Valeur** : Vue synthétique de l'évolution de sa spécialité
- **Exemple** : Oncologue — alerté automatiquement quand un signal fort émerge sur une combinaison thérapeutique inattendue

---

## 5. Concepts clés

### 5.1 Signal faible émergent

Un **signal faible** est une association (entité ↔ entité) qui :
- N'existait pas ou peu dans le KG il y a N semaines
- Apparaît dans des publications récentes provenant d'équipes indépendantes
- Présente une trajectoire de croissance rapide

**Exemple** : L'association "GLP-1 ↔ Alzheimer" passe de 0 mentions à 5 mentions en 3 semaines, provenant de 3 pays différents → signal fort d'émergence.

### 5.2 Knowledge Graph temporel

Le KG n'est pas une photo statique. C'est un **film** :
- Chaque semaine, un nouveau snapshot du KG est calculé
- La comparaison entre snapshots révèle :
  - **Nouvelles entités** (nœuds qui apparaissent)
  - **Nouvelles relations** (arêtes qui apparaissent)
  - **Relations qui se renforcent** (poids qui augmente)
  - **Relations qui déclinent** (poids qui diminue)

### 5.3 Score d'émergence

Score composite qui quantifie la "nouveauté" d'une entité ou relation :

```
Score d'émergence = f(
    nouveauté,          → Depuis quand cette relation existe-t-elle ?
    vélocité,           → À quelle vitesse progresse-t-elle ?
    diversité_sources,  → Combien d'équipes/pays indépendants ?
    impact_journals     → Dans quels journaux sont les publications ?
)
```

Un score élevé signifie : "Cette association mérite votre attention, quelque chose est en train de naître."

### 5.4 Phases de maturité d'un signal

```
⚫ Silence        → 0 mention
🔴 Premiers murmures → 1-3 mentions, 1-2 équipes
🟡 Signal émergent   → 4-10 mentions, 3+ équipes indépendantes
🟢 Tendance confirmée → 10+ mentions, revues systématiques apparaissent
🔵 Consensus         → Présent dans les guidelines, enseigné
```

Le système cible la détection des phases **🔴 → 🟡** (là où la valeur est maximale).

### 5.5 Assertion Status (OpenMed)

L'extraction NER seule ne suffit pas. Savoir qu'un article mentionne "Semaglutide" et "Alzheimer" ne dit pas si l'article **confirme**, **réfute** ou **spécule** sur un lien. L'**Assertion Status** qualifie chaque entité extraite :

| Statut | Signification | Exemple |
|--------|--------------|--------|
| **PRESENT** | L'entité est affirmée comme réelle/active | "Le patient présente une hypertension" |
| **ABSENT / NEGATED** | L'entité est explicitement niée | "Pas d'amélioration cognitive observée" |
| **HYPOTHETICAL** | L'entité est supposée ou conditionnelle | "Des essais supplémentaires sont nécessaires" |
| **HISTORICAL** | L'entité est mentionnée au passé | "Antécédent de diabète de type 2" |

Cette qualification transforme le KG d'un graphe de **cooccurrences** en un graphe de **relations qualifiées**.

### 5.6 Score de consensus scientifique

Pour chaque relation (entité_A ↔ entité_B), le score de consensus agrège les assertion status de tous les articles sources :

```
Consensus(A ↔ B) = {
    positif:      Nb articles [PRESENT]     / Total,
    négatif:      Nb articles [NEGATED]     / Total,
    hypothétique: Nb articles [HYPOTHETICAL] / Total
}
```

**Exemple** : "Semaglutide ↔ Alzheimer" — 5 articles, 3 PRESENT, 1 NEGATED, 1 HYPOTHETICAL → **Consensus 60% positif, signal contradictoire**.

Ce score répond à la question : **"La communauté scientifique est-elle d'accord sur cette association ?"**

### 5.7 Zero-shot NER (entités custom)

Les modèles NER standard d'OpenMed extraient des catégories fixes (DISEASE, DRUG, GENE...). Le **Zero-shot NER** (via GLiNER intégré à OpenMed) permet à l'utilisateur de définir **ses propres types d'entités** sans re-entraîner de modèle :

```python
# L'utilisateur définit ses entités custom dans l'interface
custom_labels = ["BRAIN_REGION", "IMAGING_TECHNIQUE", "BIOMARKER", "COGNITIVE_FUNCTION"]

# OpenMed Zero-shot extrait ces entités depuis les abstracts PubMed
result = analyze_text(abstract, labels=custom_labels, model="zeroshot")
```

Cela rend BioHorizon **adaptable à n'importe quel sous-domaine** (neurosciences, oncologie, cardiologie...) sans modification du code.

---

## 6. Architecture fonctionnelle

### Vue d'ensemble du flux

```
┌────────────────────────────────────────────────────────────────────┐
│                        UTILISATEUR                                  │
│                                                                    │
│  "Surveille l'évolution des traitements pour Alzheimer"            │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                    1. COLLECTE (PubMed)                             │
│                                                                    │
│  Requête PubMed → Articles récents (titre, abstract, MeSH, PMID)  │
│  Fréquence : quotidienne ou hebdomadaire                           │
│  Filtres : dates, types de publication, journaux, espèces          │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│              2. EXTRACTION (OpenMed — 3 couches)                    │
│                                                                    │
│  2a. NER standard → DISEASE, DRUG, GENE, PROTEIN, ANATOMY         │
│  2b. Zero-shot NER → entités custom (BRAIN_REGION, BIOMARKER...)   │
│  2c. Assertion Status → PRESENT / NEGATED / HYPOTHETICAL / PAST    │
│                                                                    │
│  Sortie : entités + type + confiance + assertion status            │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│         3. CONSTRUCTION DU KNOWLEDGE GRAPH QUALIFIÉ                │
│                                                                    │
│  Nœuds = entités extraites (normalisées, dédupliquées)             │
│  Arêtes = cooccurrences dans un même abstract                      │
│  Poids = fréquence × confiance moyenne                             │
│  Assertion = PRESENT / NEGATED / HYPOTHETICAL par article          │
│  Métadonnées = PMIDs sources, dates, journaux                      │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│        4. ANALYSE TEMPORELLE, DÉTECTION & CONSENSUS                │
│                                                                    │
│  Comparaison KG(semaine N) vs KG(semaine N-4)                      │
│  Calcul des deltas : nouvelles entités, nouvelles relations        │
│  Scoring d'émergence pour chaque delta                             │
│  Score de consensus : % positif / négatif / hypothétique           │
│  Classification : signal confirmé / contradictoire / hypothétique  │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│               5. PRÉSENTATION & INTERACTION                        │
│                                                                    │
│  Dashboard : signaux classés par score + consensus                 │
│  KG interactif : visualisation avec codes couleur temporels        │
│  Timeline : évolution des entités/relations dans le temps          │
│  RAG : questions/réponses sourcées avec citations PMID             │
│  Alertes : notifications sur signaux forts                         │
│  Export LinkRdata : entités + relations structurées                │
└────────────────────────────────────────────────────────────────────┘
```

---

## 7. Architecture technique

### Vue d'ensemble des composants

```
┌─────────────────────────────────────────────────────────────────────┐
│                      FRONTEND (Next.js)                              │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  ┌────────┐ │
│  │  Dashboard    │  │  KG Viewer    │  │  Timeline    │  │  Chat  │ │
│  │  (signaux)    │  │  (graphe)     │  │  (évolution) │  │  (RAG) │ │
│  └──────────────┘  └───────────────┘  └──────────────┘  └────────┘ │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ API REST / WebSocket
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                                │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    API Layer (routes)                         │   │
│  │  /pubmed/search  /ner/extract  /kg/*  /signals/*  /ask       │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                              │                                      │
│  ┌──────────────────────────▼───────────────────────────────────┐   │
│  │                  Agent intelligent                            │   │
│  │  Orchestration via Deep Agents (LangChain/LangGraph)          │   │
│  │  Tools : search_pubmed, extract_entities, assert_status,      │   │
│  │          build_kg, detect_signals, score_consensus, query_rag  │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                              │                                      │
│  ┌──────────┐  ┌───────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │  PubMed  │  │  OpenMed      │  │  KG Engine   │  │  Signal   │ │
│  │  Client  │  │  ┌─ NER      │  │  (NetworkX)  │  │  Detector │ │
│  │          │  │  ├─ Zero-shot│  │              │  │  +Consensus│ │
│  │          │  │  └─ Assert.  │  │              │  │  Scorer   │ │
│  └──────────┘  └───────────────┘  └──────────────┘  └───────────┘ │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      STOCKAGE                                        │
│                                                                     │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────────┐ │
│  │  Supabase    │  │  Redis        │  │  Fichiers KG (snapshots) │ │
│  │  (PostgreSQL │  │  (cache       │  │  (JSON / GraphML par     │ │
│  │  + vectors)  │  │   requêtes)   │  │   semaine)               │ │
│  └──────────────┘  └───────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Flux de données détaillé

```
                    ┌──────────────┐
                    │  Scheduler   │ (cron hebdomadaire)
                    └──────┬───────┘
                           │
            ┌──────────────▼──────────────┐
            │  Pour chaque requête sauvée  │
            └──────────────┬──────────────┘
                           │
         ┌─────────────────▼─────────────────┐
         │  1. PubMed ESearch + EFetch        │
         │     → PMIDs + articles (7 derniers │
         │       jours)                       │
         └─────────────────┬─────────────────┘
                           │
         ┌─────────────────▼───────────────────────┐
         │  2. OpenMed (3 couches, batch)       │
         │     2a. NER standard → entités       │
         │     2b. Zero-shot → entités custom   │
         │     2c. Assertion Status → qualifie   │
         └─────────────────┬───────────────────────┘
                           │
         ┌─────────────────▼───────────────────────┐
         │  3. Mise à jour KG qualifié          │
         │     → Ajout nœuds/arêtes             │
         │     → Assertion par article/relation │
         │     → Mise à jour poids/fréquences   │
         │     → Sauvegarde snapshot semaine N   │
         └─────────────────┬───────────────────────┘
                           │
         ┌─────────────────▼───────────────────────┐
         │  4. Détection + Consensus             │
         │     → Diff(KG_N, KG_N-4)              │
         │     → Calcul scores d'émergence        │
         │     → Score consensus par relation      │
         │       (% positif/négatif/hypothétique)  │
         │     → Classification des signaux        │
         └─────────────────┬───────────────────────┘
                           │
         ┌─────────────────▼───────────────────────┐
         │  5. Génération rapport + export        │
         │     → Signaux émergents triés          │
         │     → Tendances + déclins              │
         │     → Score de consensus par signal     │
         │     → Envoi alerte si score > seuil     │
         │     → Export LinkRdata (JSON-LD / RDF)  │
         └─────────────────────────────────────────┘
```

---

## 8. Arborescence du projet

> **Légende** : ✅ = existe | 🔨 = à créer | 🔄 = à refactorer

```
med-assist/
├── biomed-rag/                              # Backend Python
│   │
│   ├── main.py                     ✅    # Point d'entrée FastAPI
│   ├── requirements.txt            ✅    # Dépendances Python
│   ├── .env                        ✅    # Variables d'environnement
│   ├── Dockerfile                  ✅    # Image Docker backend
│   │
│   │   ══════════════════════════════════════════════
│   │   API LAYER (FastAPI)
│   │   ══════════════════════════════════════════════
│   │
│   ├── api/                        ✅    # API FastAPI
│   │   ├── router.py               ✅    # Routeur principal (combine les sub-routers)
│   │   │   # (agent_lc.py supprimé — legacy, remplacé par /ask → Deep Agent)
│   │   ├── routes/
│   │   │   ├── health.py           ✅    # GET /health
│   │   │   ├── ask.py              ✅    # POST /ask (délègue au Deep Agent)
│   │   │   ├── upload.py           ✅    # POST /upload (upload PDF + indexation)
│   │   │   ├── pubmed.py           ✅    # /pubmed/* (recherche PubMed)
│   │   │   ├── ner.py              ✅    # /ner/* (extraction NER)
│   │   │   ├── kg.py               ✅    # /kg/* (Knowledge Graph)
│   │   │   ├── signals.py          🔨    # /signals/* (détection signaux)
│   │   │   ├── conversations.py    ✅    # /conversations/* (CRUD conversations)
│   │   │   ├── users.py            ✅    # /users/* (gestion utilisateurs)
│   │   │   ├── topics.py           ✅    # /topics/* (sujets de veille)
│   │   │   └── cache.py            ✅    # /cache/* (gestion cache Redis)
│   │   └── schemas/
│   │       ├── common.py           ✅    # Schémas partagés
│   │       ├── pubmed.py           ✅    # Schémas requête/réponse PubMed
│   │       ├── ner.py              ✅    # Schémas entités NER
│   │       ├── signals.py          🔄    # Schémas signaux (à compléter)
│   │       ├── topic.py            ✅    # Schémas sujets de veille
│   │       └── user.py             ✅    # Schémas utilisateurs
│   │
│   │   ══════════════════════════════════════════════
│   │   DEEP AGENTS (LangChain / LangGraph)
│   │   ══════════════════════════════════════════════
│   │
│   ├── deepagents/                 ✅    # Module Deep Agents (orchestration)
│   │   ├── __init__.py             ✅    # Export : create_biomedical_agent
│   │   │   # (router.py supprimé — /ask unifié dans api/routes/ask.py)
│   │   ├── memory.py               ✅    # Mémoire unifiée (dual-write Supabase + in-memory)
│   │   │
│   │   ├── agents/                        # Agents intelligents
│   │   │   ├── main_agent.py       🔄    # Agent principal (→ migrer vers LangGraph)
│   │   │   ├── pubmed_agent.py     🔨    # Sub-agent PubMed (recherche + filtrage)
│   │   │   ├── ner_agent.py        🔨    # Sub-agent NER (extraction + assertion)
│   │   │   ├── signal_agent.py     🔨    # Sub-agent Signaux (détection + consensus)
│   │   │   └── prompts.py          🔨    # Prompts système pour chaque agent
│   │   │
│   │   ├── graph/                  🔨    # LangGraph workflows
│   │   │   ├── surveillance.py     🔨    # Workflow : PubMed → NER → KG → Signaux
│   │   │   ├── ask_workflow.py     🔨    # Workflow : question → RAG → réponse
│   │   │   └── nodes.py           🔨    # Nœuds LangGraph réutilisables
│   │   │
│   │   ├── tools/                         # Outils LangChain (bindés aux agents)
│   │   │   ├── document/           ✅    # Outils documents
│   │   │   │   ├── pdf_loader.py   ✅    # Parsing PDF (PyMuPDF, OCR)
│   │   │   │   ├── store_pdf.py    ✅    # Stockage PDF dans Supabase
│   │   │   │   ├── vector_store.py ✅    # Indexation vectorielle
│   │   │   │   ├── summarizer.py   ✅    # Résumé de documents
│   │   │   │   └── query_cache.py  ✅    # Cache de requêtes
│   │   │   ├── knowledge/          ✅    # Outils connaissances
│   │   │   │   └── rag_tool.py     ✅    # Retrieval-Augmented Generation
│   │   │   ├── biomedical/         🔨    # Outils biomédicaux (à implémenter)
│   │   │   │   ├── pubmed_tool.py  🔨    # Wrapper PubMed pour l'agent
│   │   │   │   ├── ner_tool.py     🔨    # Wrapper NER pour l'agent
│   │   │   │   ├── kg_tool.py      🔨    # Wrapper KG pour l'agent
│   │   │   │   └── signal_tool.py  🔨    # Wrapper signaux pour l'agent
│   │   │   └── utility/                   # Utilitaires
│   │   │
│   │   └── workflows/              🔨    # Workflows planifiés (à implémenter)
│   │       └── weekly_surveillance.py 🔨 # Pipeline hebdo automatisé
│   │
│   │   ══════════════════════════════════════════════
│   │   OUTILS MÉTIER (logique partagée API + agents)
│   │   ══════════════════════════════════════════════
│   │
│   ├── core_tools/                 ✅    # Outils métier standalone (appelables hors agent)
│   │   ├── pubmed_tool.py          ✅    # Recherche PubMed (NCBI E-utilities)
│   │   ├── ner_tool.py             ✅    # Extraction entités (wrapper)
│   │   └── kg_tool.py              ✅    # Construction et requête KG
│   │
│   ├── ner/                        ✅    # Module NER (OpenMed)
│   │   ├── backends/
│   │   │   ├── openmed_backend.py  ✅    # Backend OpenMed (NER standard)
│   │   │   ├── openmed_zeroshot.py 🔨    # Backend OpenMed Zero-shot (entités custom)
│   │   │   └── gliner_backend.py   ✅    # Backend GLiNER (fallback)
│   │   ├── assertion.py            🔨    # Assertion Status (PRESENT/NEGATED/HYPO/PAST)
│   │   ├── schemas.py              ✅    # Dataclasses NER (NerEntity, NerResult)
│   │   └── router.py               ✅    # Routeur NER (sélection backend)
│   │
│   ├── kg/                         ✅    # Module Knowledge Graph
│   │   ├── build.py                ✅    # Construction KG (NetworkX)
│   │   ├── query.py                ✅    # Requêtes sur le KG
│   │   ├── normalize.py            ✅    # Normalisation entités (MeSH, UMLS)
│   │   ├── schemas.py              ✅    # Dataclasses KG (nœuds, arêtes)
│   │   ├── store.py                ✅    # Persistance KG (fichiers)
│   │   └── snapshots.py            🔨    # Gestion snapshots temporels
│   │
│   ├── rag/                        ✅    # Module RAG
│   │   ├── chain.py                ✅    # Chaîne LangChain RAG
│   │   ├── retriever.py            ✅    # Retriever avec KG enrichment
│   │   └── vector_store.py         ✅    # Gestion du vector store
│   │
│   ├── signals/                    🔨    # Module détection de signaux (À CRÉER)
│   │   ├── detector.py             🔨    # Algorithme de détection
│   │   ├── scoring.py              🔨    # Calcul score d'émergence
│   │   ├── consensus.py            🔨    # Score de consensus (positif/négatif/hypothétique)
│   │   ├── classifier.py           🔨    # Classification (émergent/tendance/déclin)
│   │   └── reporter.py             🔨    # Génération de rapports
│   │
│   │   ══════════════════════════════════════════════
│   │   STOCKAGE & SERVICES
│   │   ══════════════════════════════════════════════
│   │
│   ├── storage/                    ✅    # Couche de persistance
│   │   ├── supabase_client.py      ✅    # Client Supabase singleton
│   │   ├── kg_repository.py        ✅    # Repository KG (Supabase)
│   │   └── kg_cache_redis.py       ✅    # Cache KG (Redis)
│   │
│   │   # (memory/ supprimé — fusionné dans deepagents/memory.py)
│   │
│   ├── services/                   ✅    # Services métier
│   │   ├── topic_service.py        ✅    # Gestion des sujets de veille
│   │   └── user_service.py         ✅    # Gestion préférences utilisateur
│   │
│   ├── config/                     ✅    # Configuration
│   │   ├── config.py               ✅    # Variables d'environnement, encodage, CORS
│   │   └── __init__.py
│   │
│   ├── database/                   ✅    # Migrations SQL
│   │   └── migrations/
│   │
│   │   ══════════════════════════════════════════════
│   │   MODULES À CRÉER (phases futures)
│   │   ══════════════════════════════════════════════
│   │
│   ├── scheduler/                  🔨    # Tâches planifiées
│   │   ├── weekly_update.py        🔨    # Mise à jour hebdomadaire KG
│   │   └── alert_dispatcher.py     🔨    # Envoi alertes signaux forts
│   │
│   ├── export/                     🔨    # Module export interopérabilité
│   │   ├── linkrdata_export.py     🔨    # Export JSON-LD / RDF pour LinkRdata
│   │   └── report_export.py        🔨    # Export PDF / JSON rapports
│   │
│   ├── data/                              # Données locales
│   │   └── kg_snapshots/                  # Snapshots KG par semaine
│   │
│   │   ══════════════════════════════════════════════
│   │   TESTS
│   │   ══════════════════════════════════════════════
│   │
│   ├── tests/                      ✅    # Tests
│   │   └── ...
│   ├── test_deepagents.py          ✅    # Tests Deep Agents
│   ├── test_pubmed_kg.py           ✅    # Tests PubMed → KG pipeline
│   └── test_rag_kg.py              ✅    # Tests RAG + KG
│
├── ui-biomed-rag/                            # Frontend Next.js
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx              # Page d'accueil (dashboard signaux)
│   │   │   ├── ask/
│   │   │   │   └── page.tsx          # Page RAG conversationnel
│   │   │   ├── pubmed/
│   │   │   │   └── page.tsx          # Page recherche PubMed
│   │   │   ├── ner/
│   │   │   │   └── page.tsx          # Page extraction NER
│   │   │   ├── graph/
│   │   │   │   └── page.tsx          # Page Knowledge Graph interactif
│   │   │   ├── signals/
│   │   │   │   └── page.tsx          # Page signaux émergents
│   │   │   ├── timeline/
│   │   │   │   └── page.tsx          # Page évolution temporelle
│   │   │   └── settings/
│   │   │       └── page.tsx          # Page configuration veille
│   │   │
│   │   ├── components/
│   │   │   ├── ui/                   # Composants shadcn/ui
│   │   │   ├── KnowledgeGraph.tsx    # Visualisation graphe interactif
│   │   │   ├── SignalCard.tsx         # Carte d'un signal émergent
│   │   │   ├── SignalDashboard.tsx    # Dashboard signaux
│   │   │   ├── ConsensusBar.tsx       # Barre de consensus (% positif/négatif)
│   │   │   ├── EntityTimeline.tsx     # Timeline d'une entité
│   │   │   ├── EmergenceScore.tsx     # Affichage score d'émergence
│   │   │   └── PubmedArticle.tsx      # Carte article PubMed
│   │   │
│   │   ├── features/
│   │   │   ├── rag/                  # Logique RAG
│   │   │   ├── signals/             # Logique signaux côté client
│   │   │   └── graph/               # Logique graphe côté client
│   │   │
│   │   └── lib/
│   │       ├── api.ts                # Client API backend
│   │       └── types.ts              # Types TypeScript
│   │
│   ├── package.json
│   └── next.config.ts
│
├── supabase/                         # Configuration Supabase
│   └── config.toml
│
└── .gitignore
```

### Architecture Deep Agents — cible

Le module `deepagents/` est l'**orchestrateur central** du projet. Il doit évoluer depuis le `SimpleAgentExecutor` actuel (boucle LLM ↔ tools basique) vers une architecture **LangGraph** avec sub-agents spécialisés :

```
┌─────────────────────────────────────────────────────────────┐
│            Agent Principal (LangGraph StateGraph)             │
│                                                              │
│  State: { query, articles, entities, kg, signals, report }   │
│                                                              │
│     ┌─── Planning (write_todos) ──────┐                     │
│     │                                  │                     │
│     ▼                                  ▼                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐    │
│  │ PubMed     │  │ NER        │  │ Signal             │    │
│  │ Sub-Agent  │  │ Sub-Agent  │  │ Sub-Agent          │    │
│  │            │  │            │  │                    │    │
│  │ • search   │  │ • extract  │  │ • detect           │    │
│  │ • filter   │  │ • zeroshot │  │ • score_consensus  │    │
│  │ • fetch    │  │ • assert   │  │ • classify         │    │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────────────┘    │
│        │               │               │                    │
│        └───────────────┼───────────────┘                    │
│                        ▼                                    │
│               Filesystem Backend                            │
│        (résultats intermédiaires sur disque)                │
│                                                              │
│     Mémoire : ConversationMemoryManager → Supabase          │
│     Traçabilité : LangSmith                                 │
└─────────────────────────────────────────────────────────────┘
```

**Migration en 3 étapes** :
1. **Actuel** : `SimpleAgentExecutor` (boucle tool-calling) ✅
2. **Phase 2** : `StateGraph` LangGraph avec nœuds séquentiels (PubMed → NER → KG → Signaux)
3. **Phase 3** : Sub-agents autonomes avec planning (`write_todos`), filesystem backend, mémoire persistante

### Relation `core_tools/` vs `deepagents/tools/`

| Répertoire | Rôle | Appelé par |
|------------|------|----------|
| `core_tools/` | Logique métier standalone (PubMed, NER, KG) | API routes directement |
| `deepagents/tools/` | Wrappers LangChain `@tool` pour l'agent | Deep Agents (via `bind_tools`) |

Les wrappers dans `deepagents/tools/biomedical/` appellent la logique de `core_tools/` en interne. Pas de duplication de logique.

---

## 9. Fonctionnalités détaillées

### F1 — Recherche PubMed avancée

**Description** : Interrogation de PubMed en temps réel via NCBI E-utilities.

**Capacités** :
- Requêtes en langage naturel ou syntaxe PubMed (MeSH, champs, booléens)
- Filtres : dates, types de publication, journaux, langues, espèces
- Pagination pour gros résultats
- Cache Redis (TTL 24h) pour éviter les requêtes répétées

**Entrée** : Requête texte + filtres  
**Sortie** : Liste d'articles (PMID, titre, abstract, auteurs, journal, date, MeSH)

---

### F2 — Extraction d'entités médicales (OpenMed — 3 couches)

**Description** : Extraction automatique d'entités biomédicales via OpenMed, en 3 couches complémentaires.

#### F2a — NER standard (modèles pré-entraînés)

**Types d'entités** :
- **DISEASE** : maladies, pathologies (ex: "Alzheimer disease", "hypertension")
- **DRUG** : médicaments, molécules (ex: "Semaglutide", "Aspirin")
- **GENE** : gènes (ex: "APOE", "BRCA1")
- **PROTEIN** : protéines (ex: "tau", "amyloid-beta")
- **ANATOMY** : organes, structures (ex: "hippocampus", "liver")
- **CHEMICAL** : composés chimiques
- **ONCOLOGY** : entités liées au cancer (mutations, tumeurs)
- **DNA/RNA** : séquences, lignées cellulaires

**Modèles** : 753+ modèles OpenMed (33M à 770M paramètres), de TinyMed (CPU) à BigMed (GPU).

#### F2b — Zero-shot NER (entités custom)

**Description** : L'utilisateur définit ses propres types d'entités sans re-entraîner de modèle.

**Exemple** :
```python
custom_labels = ["BRAIN_REGION", "IMAGING_TECHNIQUE", "BIOMARKER", "COGNITIVE_FUNCTION"]
result = analyze_text(abstract, labels=custom_labels, model="zeroshot")
```

**Use cases** :
- Neurosciences : BRAIN_REGION, COGNITIVE_FUNCTION → compatible LinkRbrain
- Oncologie : MUTATION, TUMOR_TYPE, THERAPY_LINE
- Cardiologie : CARDIAC_MARKER, RISK_FACTOR

#### F2c — Assertion Status

**Description** : Qualifier chaque entité extraite avec son statut contextuel.

| Statut | Signification | Exemple |
|--------|--------------|--------|
| **PRESENT** | Affirmé/confirmé | "Semaglutide shows neuroprotective effects" |
| **NEGATED** | Nié/réfuté | "No significant cognitive improvement observed" |
| **HYPOTHETICAL** | Supposé/conditionnel | "Further trials are needed to confirm" |
| **HISTORICAL** | Passé/antécédent | "History of type 2 diabetes" |

**Entrée** : Texte brut (titre + abstract)  
**Sortie** : Liste d'entités avec span, type, score de confiance, assertion status

---

### F3 — Knowledge Graph temporel

**Description** : Construction et maintenance d'un graphe de connaissances qui évolue dans le temps.

**Nœuds** :
- Entités médicales normalisées
- Attributs : type, fréquence totale, première apparition, dernière apparition

**Arêtes** :
- Cooccurrence dans un même abstract
- Attributs : poids (fréquence), confiance moyenne, PMIDs sources, date première/dernière occurrence

**Snapshots** :
- Un snapshot par semaine (JSON/GraphML)
- Stockage des deltas entre snapshots
- Historique glissant configurable (ex: 12 semaines)

---

### F4 — Détection de signaux émergents

**Description** : Identification automatique des entités et relations qui émergent ou qui déclinent.

**Algorithme simplifié** :

1. Charger KG(semaine N) et KG(semaine N-k)
2. Pour chaque relation dans KG(N) :
   - Si absente dans KG(N-k) → **nouvelle relation**
   - Si poids(N) > poids(N-k) × seuil → **relation en croissance**
3. Pour chaque relation dans KG(N-k) :
   - Si absente dans KG(N) ou poids en baisse → **relation en déclin**
4. Calculer le score d'émergence pour chaque delta
5. Classer : signal faible / tendance / déclin

**Score d'émergence** (pondéré) :
- **Nouveauté** (30%) : la relation est-elle récente ?
- **Vélocité** (30%) : à quelle vitesse progresse-t-elle ?
- **Diversité** (20%) : combien d'équipes/pays indépendants ?
- **Impact** (20%) : dans quels journaux (impact factor) ?

**Sortie** : Liste de signaux classés par score, avec PMIDs sources et extraits de phrases.

---

### F5 — Dashboard de signaux

**Description** : Interface web présentant les signaux de manière claire et actionnable.

**Contenu** :
- **🔴 Signaux émergents** : nouvelles associations détectées, score > 70
- **🟡 Tendances en accélération** : associations existantes en forte croissance
- **🟢 Paysage stable** : domaines sans changement significatif
- **⚫ Déclins** : sujets en perte de vitesse

Chaque signal affiche son **score de consensus** :
```
🔴 Signal émergent : Semaglutide ↔ Alzheimer
   Score d'émergence : 87/100
   📊 Consensus : ██████████░░░░░░░░░░ 60% positif
   ✅ 3 articles POSITIF | ❌ 1 NÉGATIF | ❓ 1 HYPOTHÉTIQUE
```

**Interaction** :
- Clic sur un signal → détail avec articles sources classés par assertion (positif/négatif/hypothétique)
- Filtre par type d'entité (maladies, médicaments, gènes)
- Filtre par période (dernière semaine, dernier mois, dernier trimestre)
- Filtre par consensus (confirmé / contradictoire / hypothétique)

---

### F6 — Knowledge Graph interactif

**Description** : Visualisation du KG avec coloration temporelle.

**Affichage** :
- Nœuds colorés par type (disease=rouge, drug=bleu, gene=vert)
- Taille des nœuds proportionnelle à la fréquence
- Arêtes avec épaisseur proportionnelle au poids
- **Coloration temporelle** : les nouveaux nœuds/arêtes sont mis en surbrillance

**Interaction** :
- Clic sur un nœud → articles PubMed associés
- Hover sur une arête → PMIDs sources + score d'émergence
- Zoom/pan, filtrage par type, recherche de nœud

---

### F7 — RAG conversationnel sourcé

**Description** : Agent conversationnel qui répond aux questions en s'appuyant sur le KG et les articles PubMed indexés.

**Capacités** :
- Réponses basées sur les articles PubMed récupérés
- Citations systématiques (PMIDs)
- Enrichissement par le KG (relations connues)
- Mémoire de conversation

**Exemple** :
> **Utilisateur** : "Quels signaux émergents pour l'Alzheimer ce mois-ci ?"  
> **Agent** : "3 signaux détectés : (1) GLP-1 ↔ neuroprotection (score 87, 5 articles, PMID:xxx, PMID:yyy), (2) ..."

---

### F8 — Veille automatisée

**Description** : Requêtes de veille sauvegardées, exécutées automatiquement.

**Fonctionnement** :
- L'utilisateur configure 1-5 sujets de veille
- Chaque semaine, le scheduler exécute les requêtes
- Mise à jour du KG + détection de signaux
- Envoi d'un digest (email ou webhook) si signaux détectés

---

### F9 — Score de consensus scientifique

**Description** : Pour chaque relation détectée dans le KG, calculer le niveau d'accord de la communauté scientifique en agrégeant les assertion status de tous les articles sources.

**Calcul** :
```
Consensus(A ↔ B) = {
    positif:      Nb articles [PRESENT]     / Total,
    négatif:      Nb articles [NEGATED]     / Total,
    hypothétique: Nb articles [HYPOTHETICAL] / Total
}
```

**Exemples d'interprétation** :
- Consensus > 80% positif → **Signal confirmé** (forte convergence)
- Consensus 40-60% positif → **Signal contradictoire** (la communauté est divisée)
- Consensus > 50% hypothétique → **Signal préliminaire** (encore spéculatif)

**Sortie** : Score de consensus par relation, avec détail par article (PMID + assertion).

---

### F10 — Entités custom Zero-shot

**Description** : Interface permettant à l'utilisateur de définir ses propres types d'entités à extraire, sans re-entraîner de modèle. Utilise le Zero-shot NER d'OpenMed (via GLiNER).

**Fonctionnement** :
1. L'utilisateur définit ses labels dans la page Settings (ex: `BRAIN_REGION`, `BIOMARKER`)
2. Lors de chaque ingestion PubMed, les entités custom sont extraites en parallèle des entités standard
3. Les entités custom sont intégrées dans le KG avec un flag `custom: true`

**Use cases** :
- **Neurosciences** : `BRAIN_REGION`, `COGNITIVE_FUNCTION` → compatible LinkRbrain
- **Oncologie** : `MUTATION`, `TUMOR_TYPE`, `THERAPY_LINE`
- **Cardiologie** : `CARDIAC_MARKER`, `RISK_FACTOR`

**Valeur** : Rend BioHorizon adaptable à n'importe quel sous-domaine sans modification du code.

---

### F11 — Export LinkRdata / LinkRbrain

**Description** : Exporter les entités et relations du KG dans un format structuré compatible avec la plateforme LinkRdata/LinkRbrain.

**Formats de sortie** :
- **JSON-LD** : format standard du web sémantique
- **RDF/Turtle** : triples (sujet, prédicat, objet) pour intégration dans un triple store
- **CSV** : format tabulaire simple pour import dans Dataverse

**Contenu exporté** :
- Entités avec type, fréquence, date de première apparition
- Relations avec poids, assertion status, score de consensus
- PMIDs sources pour traçabilité
- Métadonnées (date d'export, requête source, période)

**Articulation avec LinkRbrain** :
```
BioHorizon (entités + relations + PMIDs + consensus)
    │
    ▼ Export JSON-LD / RDF
    │
LinkRdata (intègre dans son KG neuroscience)
    │ Ajoute liens typés (se-localise, active, corrélé...)
    ▼
LinkRbrain (visualise sur modèle 3D du cerveau)
```

---

## 10. Stack technologique

### Backend

| Composant | Technologie | Rôle |
|-----------|------------|------|
| Framework API | **FastAPI** | API REST, validation, docs auto |
| Agent (actuel) | **LangChain** (`langchain-openai`, tool-calling) | Orchestration simple (SimpleAgentExecutor) |
| Agent (cible) | **LangGraph** + **Deep Agents** | StateGraph, sub-agents, planning, checkpointing |
| LLM | **Qwen/Mistral** (local) ou **Claude/GPT** (API) | Résumés, RAG |
| NER standard | **OpenMed NER** (753+ modèles) | Extraction entités médicales (DISEASE, DRUG, GENE...) |
| NER zero-shot | **OpenMed GLiNER** | Entités custom configurables par l'utilisateur |
| Assertion Status | **OpenMed Assertion** | Qualification PRESENT/NEGATED/HYPOTHETICAL/PAST |
| PII (optionnel) | **OpenMed PII** | Dé-identification HIPAA/RGPD (si données patients) |
| Knowledge Graph | **NetworkX** | Construction/analyse de graphes |
| Base de données | **Supabase (PostgreSQL)** | Métadonnées, utilisateurs |
| Vector store | **Supabase pgvector** | Embeddings articles |
| Cache | **Redis** | Cache requêtes PubMed |
| Scheduler | **APScheduler** ou **Celery** | Tâches périodiques |
| API externe | **NCBI E-utilities** | Recherche PubMed |
| Debugging | **LangSmith** | Traçabilité des étapes agent |

#### Pourquoi Deep Agents (et pas LangChain classique) ?

Le projet BioHorizon nécessite un agent capable de gérer des **tâches complexes multi-étapes** (PubMed → NER → KG → Détection signaux → Rapport). Un agent LangChain classique (boucle simple LLM ↔ tools) est "shallow" : il réagit au coup par coup, sans planification ni mémoire durable.

L'architecture cible repose sur **LangGraph** (graphe d'exécution) avec les capacités Deep Agents :

1. **Planning (`write_todos`)** : L'agent décompose une tâche complexe en sous-tâches avant d'agir
2. **Sub-agents** : L'agent principal délègue à des agents spécialisés (PubMed Agent, NER Agent, Signal Agent)
3. **Filesystem backend** : Les résultats intermédiaires sont stockés sur disque → pas limité par la fenêtre de contexte du LLM
4. **Mémoire long terme** : L'agent se souvient des sujets de veille et des conversations passées

> **État actuel** : Le module `deepagents/` utilise un `SimpleAgentExecutor` (boucle tool-calling basique). La migration vers LangGraph `StateGraph` est planifiée — voir section 8 "Architecture Deep Agents — cible" pour le plan de migration en 3 étapes.

### Frontend

| Composant | Technologie | Rôle |
|-----------|------------|------|
| Framework | **Next.js 15** | App web |
| Styling | **TailwindCSS** | CSS utilitaire |
| Composants UI | **shadcn/ui** | Composants accessibles |
| Graphe | **react-force-graph-2d** ou **Cytoscape.js** | Visualisation KG |
| Charts | **Recharts** | Timelines, histogrammes |
| Icônes | **Lucide** | Iconographie |

### Dépendances Python (`requirements.txt`)

> **Légende** : ✅ = présent | 🔨 = à ajouter | 🗑️ = à supprimer

| Package | Version | Statut | Rôle |
|---------|---------|--------|------|
| `fastapi` | >=0.111.0 | ✅ | Framework API |
| `uvicorn[standard]` | >=0.29.0 | ✅ | Serveur ASGI |
| `langchain` | >=0.2.0 | ✅ | Framework agent |
| `langchain-openai` | >=0.1.7 | ✅ | LLM OpenAI/OpenRouter |
| `langchain-community` | >=0.2.0 | ✅ | Intégrations communautaires |
| `langgraph` | >=0.2.0 | 🔨 | StateGraph, workflows agents |
| `langsmith` | >=0.1.0 | 🔨 | Traçabilité et debugging agents |
| `openmed` | >=0.1.0 | 🔨 | NER biomédical + zero-shot + assertion |
| `networkx` | >=3.2 | ✅ | Construction/analyse Knowledge Graph |
| `supabase` | >=2.6.0 | ✅ | Base de données + vector store |
| `redis` | >=5.0.0 | ✅ | Cache requêtes PubMed |
| `gliner2` | >=0.1.0 | ✅ | Zero-shot NER (fallback) |
| `httpx` | >=0.27.0 | ✅ | Client HTTP async (PubMed API) |
| `rdflib` | >=7.0.0 | 🔨 | Export RDF/JSON-LD pour LinkRdata |
| `apscheduler` | >=3.10.0 | 🔨 | Scheduler tâches périodiques |
| `smolagents` | >=1.2.0 | 🗑️ | Legacy — supprimer après migration |

---

## 11. Modèle de données

### Tables principales (Supabase/PostgreSQL)

```sql
-- Articles PubMed indexés
CREATE TABLE articles (
    pmid TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    abstract TEXT,
    journal TEXT,
    pub_date DATE,
    authors JSONB,
    mesh_terms JSONB,
    indexed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Entités extraites
CREATE TABLE entities (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    normalized_text TEXT,          -- Forme normalisée (MeSH/UMLS)
    entity_type TEXT NOT NULL,     -- DISEASE, DRUG, GENE, ... ou custom (BRAIN_REGION...)
    is_custom BOOLEAN DEFAULT FALSE, -- True si entité Zero-shot custom
    frequency INTEGER DEFAULT 1,
    first_seen DATE,
    last_seen DATE,
    UNIQUE(normalized_text, entity_type)
);

-- Assertions par article (lien entité ↔ article ↔ assertion)
CREATE TABLE entity_assertions (
    id SERIAL PRIMARY KEY,
    entity_id INTEGER REFERENCES entities(id),
    pmid TEXT REFERENCES articles(pmid),
    assertion_status TEXT NOT NULL,  -- 'PRESENT', 'NEGATED', 'HYPOTHETICAL', 'HISTORICAL'
    confidence FLOAT,
    context_sentence TEXT,          -- Phrase source dans l'abstract
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Relations (arêtes du KG)
CREATE TABLE relations (
    id SERIAL PRIMARY KEY,
    source_entity_id INTEGER REFERENCES entities(id),
    target_entity_id INTEGER REFERENCES entities(id),
    weight INTEGER DEFAULT 1,
    confidence_avg FLOAT,
    pmids JSONB,                  -- Liste des PMIDs sources
    -- Consensus scientifique (agrégé depuis entity_assertions)
    consensus_positive FLOAT,     -- % articles PRESENT
    consensus_negative FLOAT,     -- % articles NEGATED
    consensus_hypothetical FLOAT, -- % articles HYPOTHETICAL
    first_seen DATE,
    last_seen DATE,
    UNIQUE(source_entity_id, target_entity_id)
);

-- Snapshots KG hebdomadaires
CREATE TABLE kg_snapshots (
    id SERIAL PRIMARY KEY,
    week_label TEXT NOT NULL,      -- Ex: "2026-W12"
    snapshot_date DATE NOT NULL,
    node_count INTEGER,
    edge_count INTEGER,
    data JSONB,                   -- Graphe sérialisé
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Signaux détectés
CREATE TABLE signals (
    id SERIAL PRIMARY KEY,
    week_label TEXT NOT NULL,
    signal_type TEXT NOT NULL,     -- 'emerging', 'accelerating', 'declining', 'contradictory'
    entity_a TEXT,
    entity_b TEXT,
    emergence_score FLOAT,
    velocity FLOAT,
    source_diversity INTEGER,     -- Nb équipes/pays indépendants
    consensus_positive FLOAT,     -- % articles PRESENT
    consensus_negative FLOAT,     -- % articles NEGATED
    consensus_hypothetical FLOAT, -- % articles HYPOTHETICAL
    consensus_label TEXT,         -- 'confirmed', 'contradictory', 'preliminary'
    pmids JSONB,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sujets de veille de l'utilisateur
CREATE TABLE watch_topics (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    query TEXT NOT NULL,
    filters JSONB,
    custom_labels JSONB,          -- Labels Zero-shot custom (ex: ["BRAIN_REGION", "BIOMARKER"])
    frequency TEXT DEFAULT 'weekly',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 12. Roadmap

### Phase 1 — Fondations (Semaines 1-2)

- [ ] **PubMed** : Recherche avancée avec filtres (existant, à consolider)
- [ ] **NER** : Extraction batch avec OpenMed (existant, à consolider)
- [ ] **KG** : Construction du graphe de cooccurrences (existant, à améliorer)
- [ ] **Snapshots** : Système de sauvegarde hebdomadaire du KG
- [ ] **Tests** : Validation sur un cas d'usage (Alzheimer treatment)

### Phase 2 — Détection de signaux (Semaines 3-4)

- [ ] **Detector** : Algorithme de comparaison temporelle des snapshots
- [ ] **Scoring** : Implémentation du score d'émergence
- [ ] **Classifier** : Classification des signaux (émergent/tendance/déclin)
- [ ] **Reporter** : Génération de rapports structurés
- [ ] **API** : Endpoints `/signals/` pour le frontend

### Phase 3 — Interface utilisateur (Semaines 5-6)

- [ ] **Dashboard signaux** : Page d'accueil avec signaux classés par score
- [ ] **KG Viewer** : Visualisation graphe interactif avec coloration temporelle
- [ ] **Timeline** : Évolution d'une entité/relation dans le temps
- [ ] **Détail signal** : Vue détaillée avec articles sources

### Phase 4 — Intelligence et automatisation (Semaines 7-8)

- [ ] **RAG** : Agent conversationnel sourcé avec citations PMID
- [ ] **Veille** : Requêtes sauvegardées + scheduler hebdomadaire
- [ ] **Alertes** : Notifications sur signaux forts (score > seuil)
- [ ] **Export** : Rapports PDF/JSON

### Phase 5 — OpenMed enrichi : Assertion + Consensus + Zero-shot (Semaines 9-12)

- [ ] **Assertion Status** : Intégrer OpenMed Assertion pour qualifier PRESENT/NEGATED/HYPOTHETICAL/PAST
- [ ] **Score de consensus** : Calculer le % positif/négatif/hypothétique par relation
- [ ] **Dashboard consensus** : Barre de consensus visuelle + filtre confirmé/contradictoire
- [ ] **Zero-shot NER** : Interface pour définir des entités custom par sujet de veille
- [ ] **Tests** : Validation sur cas d'usage neurosciences (BRAIN_REGION, COGNITIVE_FUNCTION)

### Phase 6 — Interopérabilité LinkRdata (Semaines 13-14)

- [ ] **Export JSON-LD / RDF** : Entités + relations + assertions + consensus + PMIDs
- [ ] **Export CSV Dataverse** : Format tabulaire pour import LinkRdata
- [ ] **Validation** : Test d'import dans LinkRdata avec données BioHorizon

### Phase 7 — Affinement (Semaines 15+)

- [ ] Normalisation des entités (MeSH/UMLS linking)
- [ ] Amélioration du scoring avec métriques bibliométriques
- [ ] Détection automatique de contradictions (basée sur Assertion Status)
- [ ] Comparaison multi-pathologies (drug repurposing)
- [ ] PII/Dé-identification (OpenMed PII) si données patients
- [ ] Tests utilisateurs et itérations UX

---

## 13. Positionnement et différenciation

### Ce que BioHorizon fait que les autres ne font pas

| Capacité | PubMed | Gargantext | BioKGrapher | PKG 2.0 | **BioHorizon** |
|----------|--------|-----------|-------------|---------|-------------|
| Recherche d'articles | ✅ | ✅ | ❌ | ❌ | ✅ |
| NER médical spécialisé | ❌ | ❌ | ✅ (ScispaCy) | ❌ | ✅ (OpenMed 753+ modèles) |
| **NER Zero-shot custom** | ❌ | ❌ | ❌ | ❌ | **✅** (OpenMed GLiNER) |
| **Assertion Status** | ❌ | ❌ | ❌ | ❌ | **✅** (PRESENT/NEGATED/HYPO) |
| Knowledge Graph | ❌ | ✅ (cooccurrences) | ✅ | ✅ (statique) | ✅ (qualifié + temporel) |
| **Dimension temporelle** | ❌ | ❌ | ❌ | ❌ | **✅** |
| **Détection d'émergence** | ❌ | ❌ | ❌ | ❌ | **✅** |
| **Score de consensus** | ❌ | ❌ | ❌ | ❌ | **✅** (% positif/négatif) |
| RAG conversationnel | ❌ | ❌ | ❌ | ❌ | ✅ |
| Veille automatisée | ✅ (alertes brutes) | ❌ | ❌ | ❌ | ✅ (intelligente) |
| **Export LinkRdata** | ❌ | ❌ | ❌ | ❌ | **✅** (JSON-LD / RDF) |
| Interface web moderne | ✅ | ✅ | ❌ | ❌ | ✅ |

### Le positionnement unique

> BioHorizon est un **sismographe de la science biomédicale** : il ne montre pas ce qui existe, il détecte ce qui est en train de naître, mesure si la communauté scientifique est d'accord, et alimente les plateformes de connaissances comme LinkRdata/LinkRbrain.

---

## 14. Risques et mitigations

| Risque | Impact | Probabilité | Mitigation |
|--------|--------|-------------|------------|
| **Rate limit NCBI** | Impossible de collecter suffisamment d'articles | Moyenne | Clé API NCBI (10 req/s), cache Redis, requêtes batch |
| **Bruit NER** | Faux positifs dans les entités extraites | Haute | Seuil de confiance (0.7), normalisation, validation manuelle |
| **Faux signaux** | L'utilisateur est alerté pour rien | Moyenne | Score d'émergence composite, seuil configurable, diversité des sources |
| **Volume de données** | KG trop gros, performances dégradées | Moyenne | Fenêtre glissante (12 semaines), agrégation, pruning des nœuds faibles |
| **Abstracts manquants** | Certains articles PubMed n'ont pas d'abstract | Haute | Filtrage à l'import, fallback sur titre + MeSH terms |
| **Normalisation** | "Alzheimer's disease" ≠ "AD" ≠ "Alzheimer disease" | Haute | Mapping MeSH/UMLS, regroupement de synonymes, normalisation progressive |
| **Interprétation** | L'utilisateur confond "signal émergent" avec "vérité scientifique" | Moyenne | Disclaimers clairs, affichage des PMIDs sources, scoring transparent |
| **Assertion Status pas encore dispo** | Modèle OpenMed Assertion en roadmap Q1 2026 | Moyenne | Commencer sans assertion, ajouter dès disponible. Fallback : heuristiques négation (regex) |
| **Zero-shot bruit** | Entités custom moins précises que NER entraîné | Haute | Seuil de confiance élevé (0.8), validation manuelle initiale, affinage itératif |
| **Interop LinkRdata** | Formats d'export incompatibles | Moyenne | Valider le format avec l'équipe LinkRdata avant implémentation |

---

## 15. Interopérabilité LinkRdata / LinkRbrain

### Contexte

**LinkRbrain** (linkrbrain.org) est une plateforme web pour l'intégration multi-échelle de données cérébrales (anatomiques, fonctionnelles, génétiques), créée par Salma Mesmoudi (Paris 1 Panthéon-Sorbonne, CNRS). **LinkRdata** (linkrdata.fr) en est l'extension vers le web sémantique, générant des graphes de connaissances fiables pour les neurosciences.

### Positionnement de BioHorizon

BioHorizon ne chevauche PAS LinkRdata/LinkRbrain. Il se positionne **en amont** comme fournisseur de données structurées :

```
Littérature PubMed (brute)
        │
        ▼
   ┌─────────────┐
   │  BioHorizon   │  ← CE PROJET
   │  (veille +  │     Extraction + détection + traçabilité
   │   NER +     │     + assertion + consensus
   │   signaux)  │
   └──────┬──────┘
          │
          │ Export JSON-LD / RDF
          │ (entités + relations + PMIDs + consensus)
          ▼
   ┌─────────────┐
   │  LinkRdata  │  
   │  (KG neuro- │     Intégration multi-échelle +
   │   science   │     liens typés (se-localise, active, corrélé...)
   │   fiable)   │
   └──────┬──────┘
          │
          ▼
   ┌─────────────┐
   │  LinkRbrain │  ← PLATEFORME EXISTANTE
   │  (visu 3D   │     Exploration interactive cerveau
   │   cerveau)  │
   └─────────────┘
```

### Valeur ajoutée de BioHorizon pour LinkRdata

| Ce que BioHorizon fournit | Ce que LinkRdata en fait |
|------------------------|------------------------|
| Entités médicales (DISEASE, DRUG, GENE...) | Les intègre comme nœuds dans son KG |
| Entités custom (BRAIN_REGION, COGNITIVE_FUNCTION) | Les relie à ses données cérébrales (IRMf, connectivité) |
| Assertion Status (PRESENT/NEGATED) | Qualifie la fiabilité des liens |
| Score de consensus | Priorise les associations les plus solides |
| PMIDs sources | Traçabilité complète vers la littérature |
| Signaux émergents | Identifie les nouvelles pistes de recherche |

### Comparaison des domaines

| Aspect | BioHorizon | LinkRdata/LinkRbrain |
|--------|----------|---------------------|
| **Domaine** | Littérature biomédicale (toute médecine) | Neurosciences cognitives (cerveau) |
| **Source** | PubMed (articles) | Données cérébrales (IRMf, gènes, connectivité) |
| **Type de KG** | KG biomédical + temporel + consensus | KG neuroscience avec liens typés |
| **NER** | OpenMed (spécialisé médical) | SpaCy, NLTK, BERT, GPT (générique) |
| **Chevauchement** | **Aucun** | **Aucun** |
| **Complémentarité** | **Forte** | **Forte** |

---

*Document généré le 19 mars 2026. Mis à jour avec le pitch enrichi (Assertion Status, Consensus, Zero-shot NER, Export LinkRdata).*
