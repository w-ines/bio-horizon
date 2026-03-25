# Fichiers et Dossiers Obsolètes ou Inutiles — Analyse du Projet

## Résumé Exécutif

Après analyse du projet BioHorizon, voici les fichiers/dossiers **potentiellement obsolètes** ou **à supprimer** suite à la migration vers Deep Agents et l'évolution du projet.

---

## 🔴 Fichiers/Dossiers à SUPPRIMER

### **1. `/med-rag/agent/` — OBSOLÈTE (Migration vers deepagents)**

**Statut** : ❌ **À SUPPRIMER**

**Raison** :
- Contient l'ancien agent LangChain (`langchain_agent.py`)
- Remplacé par `deepagents/agents/main_agent.py`
- Utilisé uniquement par `/agent-lc` qui est lui-même legacy

**Fichiers** :
```
med-rag/agent/
├── __init__.py (vide)
├── langchain_agent.py (2894 bytes) — OBSOLÈTE
└── __pycache__/
```

**Impact de la suppression** :
- L'endpoint `/agent-lc` ne fonctionnera plus
- Mais `/agent-lc` est déjà marqué comme "Legacy" dans `main.py`
- Remplacé par `/agent-deep` (Deep Agents)

**Action recommandée** :
```bash
rm -rf biomed-rag/agent/
```

---

### **2. `/med-rag/api/agent_lc.py` — OBSOLÈTE (Legacy endpoint)**

**Statut** : ❌ **À SUPPRIMER**

**Raison** :
- Endpoint legacy `/agent-lc` qui utilise l'ancien `agent/langchain_agent.py`
- Remplacé par `deepagents/router.py` avec `/agent-deep`
- Commentaire dans le code : "Legacy LangChain agent router"

**Fichier** :
```
med-rag/api/agent_lc.py (54 lignes)
```

**Impact de la suppression** :
- L'endpoint `POST /agent-lc` ne sera plus disponible
- Le frontend doit utiliser `/agent-deep` à la place

**Action recommandée** :
```bash
rm biomed-rag/api/agent_lc.py
```

**Modification nécessaire dans `main.py`** :
```python
# SUPPRIMER ces lignes :
from api.agent_lc import router as agent_lc_router
app.include_router(agent_lc_router)
```

---

### **3. `huggingsmolagent/` — OBSOLÈTE (si migration complète vers Deep Agents)**

**Statut** : ⚠️ **À SUPPRIMER APRÈS MIGRATION COMPLÈTE**

**Raison** :
- Ancien système d'agents basé sur Hugging Face smolagents
- En cours de remplacement par Deep Agents (LangChain)
- Commentaire dans `main.py` : "Smolagent (legacy — will be removed after full migration to deepagents)"

**Localisation** :
- Probablement dans un dossier séparé (non trouvé dans l'arborescence actuelle)
- Référencé dans `main.py` ligne 19 : `from huggingsmolagent.agent import app as smolagent_router`

**État actuel** :
- Encore monté dans `main.py` à `/agent` (ligne 64)
- Marqué comme "legacy"

**Action recommandée** :
- **ATTENDRE** la fin de la migration Deep Agents (Phase 5)
- Puis supprimer le dossier `huggingsmolagent/`
- Puis supprimer les lignes 17-24 et 62-67 de `main.py`

---

### **4. `/med-rag/migrations/` — DOUBLON avec `/med-rag/database/migrations/`**

**Statut** : ⚠️ **DOUBLON POTENTIEL**

**Raison** :
- Deux dossiers de migrations SQL :
  - `/med-rag/migrations/kg_tables.sql`
  - `/med-rag/database/migrations/` (mentionné dans PROJECT_SPECIFICATION.md)

**Fichiers** :
```
med-rag/migrations/
└── kg_tables.sql (2224 bytes)

med-rag/database/migrations/
└── (migrations SQL organisées)
```

**Action recommandée** :
1. Vérifier si `migrations/kg_tables.sql` est identique à un fichier dans `database/migrations/`
2. Si oui → **SUPPRIMER** `med-rag/migrations/`
3. Si non → **DÉPLACER** `kg_tables.sql` vers `database/migrations/`
4. Garder uniquement `database/migrations/` comme source unique de vérité

---

### **5. `/med-rag/venv/` — ENVIRONNEMENT VIRTUEL (ne devrait pas être versionné)**

**Statut** : ⚠️ **NE DEVRAIT PAS ÊTRE DANS GIT**

**Raison** :
- Les environnements virtuels Python ne doivent jamais être versionnés
- Devrait être dans `.gitignore`
- Chaque développeur crée son propre venv

**Action recommandée** :
```bash
# Vérifier .gitignore
echo "venv/" >> biomed-rag/.gitignore

# Supprimer du tracking Git (si versionné)
git rm -r --cached biomed-rag/venv/

# Ne PAS supprimer le dossier localement (nécessaire pour dev)
```

---

### **6. `/med-rag/agent_debug.log` — FICHIER DE LOG (ne devrait pas être versionné)**

**Statut** : ⚠️ **NE DEVRAIT PAS ÊTRE DANS GIT**

**Raison** :
- Fichier de log de 1.6 MB
- Les logs ne doivent jamais être versionnés
- Devrait être dans `.gitignore`

**Action recommandée** :
```bash
# Ajouter à .gitignore
echo "*.log" >> biomed-rag/.gitignore
echo "agent_debug.log" >> biomed-rag/.gitignore

# Supprimer du tracking Git
git rm --cached biomed-rag/agent_debug.log

# Supprimer le fichier localement
rm biomed-rag/agent_debug.log
```

---

### **7. `/med-rag/local_storage/` — DOSSIER VIDE**

**Statut** : ℹ️ **VIDE (peut être supprimé ou conservé)**

**Raison** :
- Dossier vide (0 items)
- Probablement créé pour stocker des données locales temporaires

**Action recommandée** :
- **Option 1** : Supprimer si inutilisé
- **Option 2** : Conserver et ajouter un `.gitkeep` si nécessaire pour la structure
- **Option 3** : Ajouter à `.gitignore` si destiné aux données locales

```bash
# Si on veut le garder mais vide dans Git :
touch biomed-rag/local_storage/.gitkeep
echo "local_storage/*" >> biomed-rag/.gitignore
echo "!local_storage/.gitkeep" >> biomed-rag/.gitignore
```

---

## 🟡 Fichiers/Dossiers à VÉRIFIER

### **8. `/med-rag/deepagents/tools/utility/` — OUTILS NON IMPLÉMENTÉS**

**Statut** : 🔨 **À IMPLÉMENTER OU SUPPRIMER**

**Raison** :
- Dossier créé mais outils non implémentés
- Mentionnés dans la roadmap mais pas dans les use cases du projet

**Fichiers mentionnés dans README** :
- `weather_tool.py` — ❓ Pas pertinent pour un projet biomédical
- `web_search_tool.py` — ✅ Potentiellement utile

**Action recommandée** :
1. **Supprimer** `weather_tool.py` (hors scope biomédical)
2. **Implémenter** `web_search_tool.py` si nécessaire pour la recherche web
3. Ou **supprimer** le dossier `utility/` si aucun outil utilitaire n'est prévu

---

### **9. `/med-rag/deepagents/agents/` — AGENTS NON IMPLÉMENTÉS**

**Statut** : 🔨 **À IMPLÉMENTER (Phase 3)**

**Raison** :
- Fichiers créés mais vides ou quasi-vides
- Prévus pour la Phase 3 (Sub-agents spécialisés)

**Fichiers** :
```
deepagents/agents/
├── main_agent.py (11294 bytes) ✅ IMPLÉMENTÉ
├── ner_agent.py (0 bytes) 🔨 VIDE
├── pubmed_agent.py (41 bytes) 🔨 QUASI-VIDE
├── signal_agent.py (46 bytes) 🔨 QUASI-VIDE
└── prompts.py (37 bytes) 🔨 QUASI-VIDE
```

**Action recommandée** :
- **Conserver** pour la Phase 3
- Ou **supprimer** les fichiers vides et les recréer quand nécessaire
- Ajouter des TODO comments pour clarifier le statut

---

### **10. `/med-rag/deepagents/graph/` — WORKFLOWS NON IMPLÉMENTÉS**

**Statut** : 🔨 **À IMPLÉMENTER (Phase 4)**

**Raison** :
- Dossier créé pour les workflows LangGraph
- Prévu pour la Phase 4 mais pas encore implémenté

**Action recommandée** :
- **Conserver** pour la Phase 4
- Ou **supprimer** et recréer quand nécessaire

---

## 🟢 Fichiers/Dossiers à CONSERVER

### **11. `/med-rag/core_tools/` — LOGIQUE MÉTIER STANDALONE**

**Statut** : ✅ **CONSERVER**

**Raison** :
- Contient la logique métier réutilisable
- Utilisé par les API routes ET par les Deep Agents tools
- Pas de duplication, juste des wrappers dans `deepagents/tools/`

---

### **12. `/med-rag/ner/`, `/med-rag/kg/`, `/med-rag/signals/`, `/med-rag/rag/`**

**Statut** : ✅ **CONSERVER**

**Raison** :
- Modules métier essentiels du projet
- Utilisés par les core_tools et les Deep Agents

---

## 📋 Plan d'Action Recommandé

### **Phase 1 : Nettoyage Immédiat (Sans Impact)**

```bash
# 1. Supprimer les logs du tracking Git
echo "*.log" >> biomed-rag/.gitignore
git rm --cached biomed-rag/agent_debug.log
rm biomed-rag/agent_debug.log

# 2. Supprimer venv du tracking Git (si versionné)
echo "venv/" >> biomed-rag/.gitignore
git rm -r --cached biomed-rag/venv/ 2>/dev/null || true

# 3. Gérer local_storage
echo "local_storage/*" >> biomed-rag/.gitignore
echo "!local_storage/.gitkeep" >> biomed-rag/.gitignore
touch biomed-rag/local_storage/.gitkeep
```

### **Phase 2 : Consolidation Migrations SQL**

```bash
# Vérifier et consolider les migrations
# Si kg_tables.sql est un doublon :
mv biomed-rag/migrations/kg_tables.sql biomed-rag/database/migrations/
rmdir biomed-rag/migrations/
```

### **Phase 3 : Suppression Legacy Agent (Après Tests)**

**⚠️ ATTENTION : Vérifier que le frontend utilise `/agent-deep` avant de supprimer**

```bash
# 1. Supprimer l'ancien agent
rm -rf biomed-rag/agent/

# 2. Supprimer l'endpoint legacy
rm biomed-rag/api/agent_lc.py

# 3. Modifier main.py
# Supprimer les lignes 15 et 60 (import et include_router agent_lc)
```

### **Phase 4 : Suppression Smolagents (Après Migration Complète)**

**⚠️ ATTENTION : Uniquement après Phase 5 de la migration Deep Agents**

```bash
# 1. Supprimer le dossier huggingsmolagent (si existe)
rm -rf huggingsmolagent/

# 2. Modifier main.py
# Supprimer les lignes 17-24 et 62-67 (smolagent import et mount)

# 3. Nettoyer requirements.txt
# Supprimer la dépendance smolagents
```

### **Phase 5 : Nettoyage Fichiers Vides (Optionnel)**

```bash
# Supprimer les fichiers agents vides (à recréer en Phase 3)
rm biomed-rag/deepagents/agents/ner_agent.py
rm biomed-rag/deepagents/agents/pubmed_agent.py
rm biomed-rag/deepagents/agents/signal_agent.py
rm biomed-rag/deepagents/agents/prompts.py

# Ou ajouter des TODO comments pour clarifier
```

---

## 📊 Résumé des Gains

| Action | Gain en Espace | Impact |
|--------|---------------|--------|
| Supprimer `agent_debug.log` | 1.6 MB | Aucun (fichier de log) |
| Supprimer `venv/` du Git | Variable | Aucun (ne devrait jamais être versionné) |
| Supprimer `agent/` | ~3 KB | ⚠️ Casse `/agent-lc` (legacy) |
| Supprimer `agent_lc.py` | ~0.5 KB | ⚠️ Casse `/agent-lc` (legacy) |
| Supprimer `huggingsmolagent/` | Variable | ⚠️ Casse `/agent` (legacy, après migration) |
| Consolider migrations | Minimal | Meilleure organisation |

---

## ✅ Checklist de Vérification Avant Suppression

Avant de supprimer les fichiers legacy, vérifier :

- [ ] Le frontend utilise `/agent-deep` et non `/agent-lc` ou `/agent`
- [ ] Tous les tests passent avec Deep Agents
- [ ] La migration Deep Agents Phase 2-3 est complète
- [ ] Aucune référence à `agent/langchain_agent.py` dans le code
- [ ] Aucune référence à `huggingsmolagent` dans le code (sauf main.py)
- [ ] Les migrations SQL sont consolidées dans `database/migrations/`
- [ ] `.gitignore` est à jour (venv, logs, local_storage)

---

## 🎯 Conclusion

**Fichiers à supprimer immédiatement** :
- ✅ `agent_debug.log` (log file)
- ✅ `venv/` du tracking Git (environnement virtuel)

**Fichiers à supprimer après vérification** :
- ⚠️ `agent/` (ancien agent LangChain)
- ⚠️ `api/agent_lc.py` (endpoint legacy)
- ⚠️ `migrations/` (doublon potentiel)

**Fichiers à supprimer après migration complète** :
- ⏳ `huggingsmolagent/` (smolagents legacy)

**Fichiers à conserver** :
- ✅ `core_tools/`, `ner/`, `kg/`, `signals/`, `rag/` (logique métier)
- ✅ `deepagents/` (nouveau système d'agents)

**Total estimé de nettoyage** : ~1.6 MB + clarification de l'architecture
