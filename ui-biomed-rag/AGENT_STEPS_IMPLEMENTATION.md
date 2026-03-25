# Implémentation de l'affichage des étapes de raisonnement de l'agent

Ce document explique comment l'affichage des étapes de raisonnement de l'agent a été implémenté dans le projet ui-rag-scrap, en s'inspirant des patterns utilisés dans le projet chat-15.

## Architecture

L'implémentation suit une architecture en 4 couches :

### 1. **Hook personnalisé : `use-agent-steps.tsx`**
- **Localisation** : `/src/features/rag/hooks/use-agent-steps.tsx`
- **Rôle** : Gère l'état global des étapes de l'agent via React Context
- **Fonctionnalités** :
  - `agentSteps`: Array contenant toutes les étapes
  - `addStep()`: Ajoute une étape
  - `resetSteps()`: Réinitialise les étapes
  - `setAgentSteps()`: Met à jour directement les étapes
  - `displayStepsProgressively()`: Affiche les étapes avec animation

### 2. **Composant d'affichage : `AgentStepsDisplay.tsx`**
- **Localisation** : `/src/features/rag/components/AgentStepsDisplay.tsx`
- **Rôle** : Affiche visuellement les étapes de raisonnement
- **Caractéristiques** :
  - Rendu markdown personnalisé (sans dépendances externes)
  - Support du texte en **gras**, du `code inline`, et des blocs de code
  - Animation de fade-in pour chaque étape
  - Indicateur de chargement pendant le traitement

### 3. **Formulaire de recherche : `SearchForm.tsx`**
- **Localisation** : `/src/features/rag/components/SearchForm.tsx`
- **Rôle** : Gère la communication avec l'API et le streaming des étapes
- **Fonctionnalités** :
  - Détecte si le streaming doit être utilisé (pas de fichiers)
  - Lit le stream SSE (Server-Sent Events) de l'API
  - Parse les données JSON et met à jour les étapes en temps réel
  - Gère la réponse finale

### 4. **Composant principal : `RagPageContent.tsx`**
- **Localisation** : `/src/components/RagPageContent.tsx`
- **Rôle** : Intègre tous les composants avec le Provider
- **Structure** :
  ```tsx
  <AgentStepsProvider>
    <SearchForm />
    <AgentStepsDisplay />
    <Result />
  </AgentStepsProvider>
  ```

## Flux de données

```
1. User entre une question
   ↓
2. SearchForm.handleSubmit()
   ↓
3. resetSteps() - Réinitialise les étapes précédentes
   ↓
4. handleStreamingRequest() - Appel API avec streaming
   ↓
5. Backend (agent.py) envoie les étapes via SSE
   ↓
6. Frontend parse les messages "data: {...}"
   ↓
7. setAgentSteps() - Ajoute chaque étape au state
   ↓
8. AgentStepsDisplay - Affiche les étapes en temps réel
   ↓
9. Réponse finale affichée dans Result
```

## Format des données streaming

Le backend (huggingsmolagent/agent.py) envoie des données au format SSE :

```
data: {"steps": ["💭 **Thought:** Analyzing the query..."], "response": null}

data: {"steps": ["🔍 **Action:** Searching the web..."], "response": null}

data: {"steps": [], "response": "Here is the final answer..."}
```

## Intégration avec le backend

Votre agent Python (`huggingsmolagent/agent.py`) utilise déjà :
- `StepTracker` pour capturer les étapes
- `generate_streaming_response()` pour le streaming SSE
- Format de données compatible avec le frontend

Le frontend est maintenant configuré pour :
1. Appeler `/api/ask` avec `stream: true`
2. Recevoir les étapes en temps réel
3. Les afficher progressivement à l'utilisateur
4. Afficher la réponse finale

## Personnalisation

### Modifier le style des étapes
Éditez `AgentStepsDisplay.tsx` pour changer les classes Tailwind :
```tsx
className="rounded-lg border border-blue-500/20 bg-blue-50/50 dark:bg-blue-950/20 p-3"
```

### Ajouter des icônes personnalisées
Les étapes du backend incluent déjà des emojis (💭, 🔍, 💻, etc.). Vous pouvez les personnaliser dans `agent.py` :
```python
formatted_steps.append(f"💭 **Thought:** {thought}")
formatted_steps.append(f"🔍 **Action:** {action}")
```

### Modifier la vitesse d'animation
Dans `use-agent-steps.tsx`, ajustez le délai :
```tsx
await new Promise(resolve => setTimeout(resolve, 300)); // 300ms entre chaque étape
```

## Points d'attention

1. **Streaming uniquement sans fichiers** : Le streaming est désactivé quand des fichiers sont uploadés (utilise la méthode classique)
2. **Gestion d'erreurs** : Les erreurs de parsing JSON sont loggées mais n'interrompent pas le stream
3. **Pas de dépendances externes** : Le renderer markdown est custom pour éviter d'ajouter react-markdown
4. **Performance** : Les étapes sont ajoutées de manière incrémentale sans re-render complet

## Prochaines étapes possibles

- [ ] Ajouter la possibilité de replier/déplier les étapes
- [ ] Sauvegarder l'historique des étapes
- [ ] Ajouter des filtres (afficher seulement certains types d'étapes)
- [ ] Exporter les étapes en format texte/JSON
- [ ] Ajouter des statistiques (temps par étape, nombre d'outils utilisés)
