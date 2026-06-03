# Installation - Knowledge Graph Visualization

## Dépendances à installer

La visualisation du Knowledge Graph nécessite `react-force-graph-2d`.

### Installation

```bash
cd ui-biomed-rag
npm install react-force-graph-2d
npm install --save-dev @types/react-force-graph-2d
```

### Vérification

Après installation, vérifier que les dépendances sont dans `package.json` :

```json
{
  "dependencies": {
    "react-force-graph-2d": "^1.25.4"
  },
  "devDependencies": {
    "@types/react-force-graph-2d": "^1.0.0"
  }
}
```

## Démarrage

### 1. Backend (FastAPI)

```bash
cd biomed-rag
python3 main.py
```

Le backend démarre sur **http://localhost:8000**

### 2. Frontend (Next.js)

```bash
cd ui-biomed-rag
npm run dev
```

Le frontend démarre sur **http://localhost:3000**

### 3. Accéder à la visualisation

Ouvrir dans le navigateur : **http://localhost:3000/knowledge-graph**

## Endpoints API disponibles

### GET /kg/stats
Statistiques du Knowledge Graph
```bash
curl http://localhost:8000/kg/stats
```

### GET /kg/graph
Données du graphe pour visualisation
```bash
# Tous les nœuds (max 100)
curl http://localhost:8000/kg/graph

# Filtrer par type d'entité
curl http://localhost:8000/kg/graph?entity_type=DRUG

# Limiter le nombre de nœuds
curl http://localhost:8000/kg/graph?max_nodes=50

# Filtrer par fréquence minimale
curl http://localhost:8000/kg/graph?min_frequency=2
```

### GET /kg/node/{node_id}
Détails d'un nœud spécifique
```bash
curl http://localhost:8000/kg/node/aspirin
```

### GET /kg/top-nodes
Top N nœuds par fréquence ou degré
```bash
curl http://localhost:8000/kg/top-nodes?n=20&sort_by=frequency
```

## Troubleshooting

### Erreur : "Module not found: react-force-graph-2d"

**Solution** : Installer la dépendance
```bash
npm install react-force-graph-2d
```

### Erreur : "Failed to fetch graph data"

**Cause** : Backend non démarré ou CORS

**Solution** :
1. Vérifier que le backend tourne sur port 8000
2. Vérifier les logs backend pour erreurs
3. Vérifier CORS dans `main.py` (doit inclure `http://localhost:3000`)

### Graphe vide

**Cause** : Knowledge Graph non peuplé

**Solution** : Enrichir le KG avec PubMed
```bash
cd biomed-rag
python3 -c "
from tools.kg_tool import ingest_from_pubmed
ingest_from_pubmed('aspirin cardiovascular', max_results=20)
"
```

### Performance lente

**Cause** : Trop de nœuds

**Solution** : Utiliser les filtres
- Réduire `max_nodes` (50 au lieu de 100)
- Augmenter `min_frequency` (2 ou 3)
- Filtrer par `entity_type`

## Features de la visualisation

✅ **Force-directed layout** : Les nœuds se positionnent automatiquement  
✅ **Couleurs par type** : DRUG (bleu), DISEASE (rouge), etc.  
✅ **Taille des nœuds** : Proportionnelle à la fréquence  
✅ **Épaisseur des liens** : Proportionnelle au poids  
✅ **Zoom/Pan** : Navigation interactive  
✅ **Click sur nœud** : Afficher détails  
✅ **Filtres** : Par type, fréquence, nombre max  
✅ **Légende** : Types d'entités avec couleurs  

## Prochaines améliorations

- [ ] Recherche de nœud par nom
- [ ] Export du graphe (PNG, SVG, JSON)
- [ ] Sous-graphe autour d'un nœud sélectionné
- [ ] Clustering visuel par communautés
- [ ] Timeline des entités (évolution temporelle)
- [ ] Comparaison de graphes (avant/après enrichissement)
