# BioHorizon — Emerging Signal Detection in Biomedical Literature

## English Version

---

### **What is BioHorizon?**

BioHorizon is an **AI-powered system for detecting emerging signals in biomedical literature**. It monitors PubMed publications, extracts medical entities, builds temporal knowledge graphs, and automatically identifies what's emerging in the scientific landscape.

---

### **The Problem**

**Researchers are drowning in information:**
- PubMed indexes **36+ million articles** and adds thousands daily
- Researchers receive 50-100 email alerts per week
- Manual triage takes 2-3 hours weekly
- **Critical emerging signals are invisible** when reading articles one by one

**Current tools answer**: *"What do we know about X?"*  
**BioHorizon answers**: *"What is emerging around X?"*

---

### **How It Works**

```
PubMed Search → Entity Extraction (OpenMed) → Knowledge Graph → Temporal Analysis → Signal Detection
```

**Key Pipeline:**
1. **Collect**: Query PubMed with advanced filters
2. **Extract**: OpenMed NER extracts diseases, drugs, genes, proteins
3. **Build**: Construct Knowledge Graph from entity co-occurrences
4. **Track**: Save weekly snapshots of the graph
5. **Detect**: Compare snapshots to identify emerging associations

---

### **Core Innovation: Temporal Knowledge Graphs**

The Knowledge Graph is not a static photo — it's a **film**:
- Weekly snapshots capture the evolving scientific landscape
- Comparison between time periods reveals:
  - **New entities** (nodes appearing)
  - **New relations** (edges appearing)
  - **Strengthening relations** (weight increasing)
  - **Declining relations** (weight decreasing)

**Example**: "GLP-1 ↔ Alzheimer" goes from 0 to 5 mentions in 3 weeks from 3 independent teams → **Strong emerging signal**

---

### **Key Features**

**1. OpenMed Integration (3 layers)**
- **Standard NER**: DISEASE, DRUG, GENE, PROTEIN, ANATOMY, CHEMICAL
- **Zero-shot NER**: Custom entities (BRAIN_REGION, BIOMARKER) without retraining
- **Assertion Status**: PRESENT / NEGATED / HYPOTHETICAL / HISTORICAL

**2. Consensus Scoring**
- Measures scientific agreement on each association
- Example: "Semaglutide ↔ Alzheimer" — 60% positive, 20% negative, 20% hypothetical → **Contradictory signal**

**3. Automated Surveillance**
- Weekly automated monitoring
- Alerts when strong signals emerge
- 4-12 weeks temporal advantage over manual monitoring

---

### **Technical Stack**

- **Backend**: Python, FastAPI, LangChain/LangGraph
- **NER**: OpenMed (state-of-the-art biomedical NER)
- **Knowledge Graph**: NetworkX
- **Database**: Supabase (PostgreSQL + JSONB)
- **Frontend**: Next.js, React, TailwindCSS
- **Data Source**: PubMed (NCBI E-utilities)

---

### **Use Cases**

**Researcher/PhD Student**
- Track 2-5 research topics
- Detect new research directions 6 weeks before colleagues
- Save 5-10 hours/week

**Biotech/Pharma**
- Competitive intelligence
- Drug repurposing opportunities
- Strategic R&D positioning

**Physician-Researcher**
- Stay current despite clinical workload
- Automatic alerts on unexpected therapeutic combinations

---

### **Current Status**

✅ **Phase 1 Complete**: Temporal KG snapshots  
✅ OpenMed integration (NER + Assertion + Zero-shot)  
✅ PubMed search with advanced filters  
✅ Knowledge Graph construction  
✅ Snapshot comparison API  

🔨 **In Progress**: Signal scoring algorithm, consensus analysis, automated reporting

---

### **Differentiation**

| Tool | What it does | What it doesn't do |
|------|-------------|-------------------|
| **PubMed Alerts** | Email new articles | No trend detection, no structure |
| **Gargantext** | Static co-occurrence maps | No temporal comparison, no medical NER |
| **BioKGrapher** | Build KG from PMIDs | No temporal dimension, no emergence detection |
| **BioHorizon** | **Temporal KG + Emergence Detection + Consensus Scoring** | ✨ |

---

### **Example Workflow**

1. User defines surveillance query: *"Alzheimer disease treatment"*
2. System runs weekly PubMed search automatically
3. Extracts entities from 50-100 new articles
4. Updates Knowledge Graph
5. Compares with 4 weeks ago
6. Detects: **15 new entities, 42 new relations, 8 strengthening relations**
7. Scores and ranks emerging signals
8. Sends weekly report with top signals

---

### **Value Proposition**

**Before BioHorizon:**
- 50-100 email alerts/week → noise
- 2-3h manual triage → time waste
- Missed emerging signals → strategic risk

**After BioHorizon:**
- Structured weekly report with scored signals
- Temporal view of scientific landscape evolution
- Automatic alerts on cross-domain bridges
- 4-12 weeks competitive advantage

---

## Version Française

---

### **Qu'est-ce que BioHorizon ?**

BioHorizon est un **système de détection de signaux émergents dans la littérature biomédicale**. Il surveille les publications PubMed, extrait des entités médicales, construit des graphes de connaissances temporels et identifie automatiquement ce qui émerge dans le paysage scientifique.

---

### **Le Problème**

**Les chercheurs sont noyés sous l'information :**
- PubMed indexe **36+ millions d'articles** et en ajoute des milliers chaque jour
- Les chercheurs reçoivent 50-100 alertes email par semaine
- Le tri manuel prend 2-3 heures par semaine
- **Les signaux émergents critiques sont invisibles** quand on lit les articles un par un

**Les outils actuels répondent** : *"Que sait-on sur X ?"*  
**BioHorizon répond** : *"Qu'est-ce qui émerge autour de X ?"*

---

### **Comment ça Marche**

```
Recherche PubMed → Extraction d'Entités (OpenMed) → Graphe de Connaissances → Analyse Temporelle → Détection de Signaux
```

**Pipeline Principal :**
1. **Collecte** : Requête PubMed avec filtres avancés
2. **Extraction** : OpenMed NER extrait maladies, médicaments, gènes, protéines
3. **Construction** : Graphe de Connaissances à partir des co-occurrences d'entités
4. **Suivi** : Sauvegarde de snapshots hebdomadaires du graphe
5. **Détection** : Comparaison des snapshots pour identifier les associations émergentes

---

### **Innovation Centrale : Graphes de Connaissances Temporels**

Le Graphe de Connaissances n'est pas une photo statique — c'est un **film** :
- Des snapshots hebdomadaires capturent l'évolution du paysage scientifique
- La comparaison entre périodes révèle :
  - **Nouvelles entités** (nœuds qui apparaissent)
  - **Nouvelles relations** (arêtes qui apparaissent)
  - **Relations qui se renforcent** (poids qui augmente)
  - **Relations qui déclinent** (poids qui diminue)

**Exemple** : "GLP-1 ↔ Alzheimer" passe de 0 à 5 mentions en 3 semaines provenant de 3 équipes indépendantes → **Signal émergent fort**

---

### **Fonctionnalités Clés**

**1. Intégration OpenMed (3 couches)**
- **NER Standard** : DISEASE, DRUG, GENE, PROTEIN, ANATOMY, CHEMICAL
- **NER Zero-shot** : Entités personnalisées (BRAIN_REGION, BIOMARKER) sans ré-entraînement
- **Statut d'Assertion** : PRESENT / NEGATED / HYPOTHETICAL / HISTORICAL

**2. Score de Consensus**
- Mesure l'accord scientifique sur chaque association
- Exemple : "Semaglutide ↔ Alzheimer" — 60% positif, 20% négatif, 20% hypothétique → **Signal contradictoire**

**3. Surveillance Automatisée**
- Monitoring hebdomadaire automatique
- Alertes quand des signaux forts émergent
- Avantage temporel de 4-12 semaines sur la veille manuelle

---

### **Stack Technique**

- **Backend** : Python, FastAPI, LangChain/LangGraph
- **NER** : OpenMed (NER biomédical état de l'art)
- **Graphe de Connaissances** : NetworkX
- **Base de Données** : Supabase (PostgreSQL + JSONB)
- **Frontend** : Next.js, React, TailwindCSS
- **Source de Données** : PubMed (NCBI E-utilities)

---

### **Cas d'Usage**

**Chercheur/Doctorant**
- Suivre 2-5 sujets de recherche
- Détecter de nouvelles directions 6 semaines avant les collègues
- Économiser 5-10 heures/semaine

**Biotech/Pharma**
- Intelligence concurrentielle
- Opportunités de repositionnement de médicaments
- Positionnement stratégique R&D

**Médecin-Chercheur**
- Rester à jour malgré la charge clinique
- Alertes automatiques sur des combinaisons thérapeutiques inattendues

---

### **État Actuel**

✅ **Phase 1 Complète** : Snapshots temporels du KG  
✅ Intégration OpenMed (NER + Assertion + Zero-shot)  
✅ Recherche PubMed avec filtres avancés  
✅ Construction du Graphe de Connaissances  
✅ API de comparaison de snapshots  

🔨 **En Cours** : Algorithme de scoring des signaux, analyse de consensus, reporting automatisé

---

### **Différenciation**

| Outil | Ce qu'il fait | Ce qu'il ne fait pas |
|-------|--------------|---------------------|
| **Alertes PubMed** | Envoie de nouveaux articles | Pas de détection de tendances, pas de structure |
| **Gargantext** | Cartes de co-occurrences statiques | Pas de comparaison temporelle, pas de NER médical |
| **BioKGrapher** | Construit un KG à partir de PMIDs | Pas de dimension temporelle, pas de détection d'émergence |
| **BioHorizon** | **KG Temporel + Détection d'Émergence + Score de Consensus** | ✨ |

---

### **Exemple de Workflow**

1. L'utilisateur définit une requête de surveillance : *"Traitement de la maladie d'Alzheimer"*
2. Le système exécute automatiquement une recherche PubMed hebdomadaire
3. Extrait les entités de 50-100 nouveaux articles
4. Met à jour le Graphe de Connaissances
5. Compare avec il y a 4 semaines
6. Détecte : **15 nouvelles entités, 42 nouvelles relations, 8 relations qui se renforcent**
7. Score et classe les signaux émergents
8. Envoie un rapport hebdomadaire avec les signaux prioritaires

---

### **Proposition de Valeur**

**Avant BioHorizon :**
- 50-100 alertes email/semaine → bruit
- 2-3h de tri manuel → perte de temps
- Signaux émergents manqués → risque stratégique

**Après BioHorizon :**
- Rapport hebdomadaire structuré avec signaux scorés
- Vue temporelle de l'évolution du paysage scientifique
- Alertes automatiques sur les ponts inter-domaines
- Avantage concurrentiel de 4-12 semaines

---

## Quick Demo Points

**Show:**
1. PubMed search interface with advanced filters
2. NER extraction with OpenMed (entities + assertion status)
3. Knowledge Graph visualization
4. Snapshot comparison showing emerging signals
5. Weekly report with scored signals

**Key Metrics:**
- 36M+ articles indexed in PubMed
- 7 entity types extracted (DISEASE, DRUG, GENE, etc.)
- Weekly snapshots for temporal tracking
- 4-12 weeks competitive advantage
- 5-10 hours/week saved per researcher
