# Agent de Recherche Spécialisé - Documentation

## Vue d'ensemble

L'agent de recherche a été enrichi avec 5 outils spécialisés utilisant l'infrastructure Composio/Exa existante. Ces outils permettent des recherches ciblées et efficaces sur le web, les actualités, les entreprises et les sources académiques.

## Architecture

### Pattern Utilisé

Suit exactement le même pattern que l'implémentation Gmail :

```
server/
├── services/
│   └── search/
│       └── exa.py                    # Service bas-niveau (MCP)
│
└── agents/
    └── execution_agent/
        └── tools/
            └── search.py              # Outils haut-niveau
```

### Composants Clés

1. **Service Exa** (`services/search/exa.py`) :
   - Communication MCP avec Composio
   - Normalisation des résultats
   - Gestion des erreurs

2. **Outils de Recherche** (`agents/execution_agent/tools/search.py`) :
   - 5 outils spécialisés
   - Logging des actions
   - Gestion d'erreurs robuste

## Outils Disponibles

### 1. `search_web` (Existant - Amélioré)
Recherche web générale via Exa.

**Paramètres** :
- `query` (requis) : Requête de recherche
- `num_results` (optionnel) : Nombre de résultats (1-20, défaut: 5)
- `include_domains` (optionnel) : Liste de domaines à prioriser
- `exclude_domains` (optionnel) : Liste de domaines à exclure

**Exemple** :
```json
{
  "query": "latest developments in quantum computing",
  "num_results": 10,
  "include_domains": ["nature.com", "science.org"]
}
```

**Améliorations** :
- ✅ Logging automatique des recherches
- ✅ Gestion d'erreurs robuste
- ✅ Comptage des résultats

---

### 2. `search_news` (Nouveau)
Recherche d'actualités récentes via des sources fiables.

**Paramètres** :
- `query` (requis) : Sujet de l'actualité
- `num_results` (optionnel) : Nombre d'articles (1-20, défaut: 10)

**Sources incluses** :
- New York Times, Wall Street Journal
- Reuters, Bloomberg, BBC
- The Guardian, CNN, AP News
- NPR, Financial Times, The Economist, Politico

**Exemple** :
```json
{
  "query": "artificial intelligence regulation europe",
  "num_results": 15
}
```

---

### 3. `research_topic` (Nouveau)
Recherche approfondie avec focus sur différents aspects.

**Paramètres** :
- `topic` (requis) : Sujet principal
- `focus_areas` (optionnel) : Aspects spécifiques à explorer
- `num_results` (optionnel) : Nombre de sources par aspect (1-20, défaut: 10)

**Exemple** :
```json
{
  "topic": "blockchain technology",
  "focus_areas": ["use cases", "challenges", "future trends"],
  "num_results": 12
}
```

**Résultat** :
```json
{
  "topic": "blockchain technology",
  "focus_areas": {
    "use cases": [...],
    "challenges": [...],
    "future trends": [...]
  },
  "total_results": 36
}
```

---

### 4. `search_company` (Nouveau)
Recherche d'informations complètes sur une entreprise.

**Paramètres** :
- `company_name` (requis) : Nom de l'entreprise
- `aspects` (optionnel) : Aspects à rechercher (défaut: ["news", "overview"])
- `num_results` (optionnel) : Résultats par aspect (1-15, défaut: 8)

**Aspects suggérés** :
- `news` : Actualités récentes
- `financials` : Informations financières
- `leadership` : Direction et management
- `products` : Produits et services
- `overview` : Vue d'ensemble

**Exemple** :
```json
{
  "company_name": "Tesla",
  "aspects": ["news", "financials", "products"],
  "num_results": 10
}
```

---

### 5. `search_academic` (Nouveau)
Recherche de publications académiques et scientifiques.

**Paramètres** :
- `query` (requis) : Sujet de recherche académique
- `num_results` (optionnel) : Nombre de sources (1-20, défaut: 10)

**Sources académiques** :
- Google Scholar
- arXiv (prépublications)
- PubMed (médecine)
- JSTOR, ScienceDirect, Springer
- Nature, Science, IEEE, ACM
- NCBI

**Exemple** :
```json
{
  "query": "machine learning interpretability techniques",
  "num_results": 15
}
```

## Gestion des Erreurs

Tous les outils incluent une gestion robuste des erreurs :

### Types d'erreurs

1. **`search_unavailable`** :
   - MCP non configuré
   - Service Exa indisponible
   - Quota dépassé

2. **`unknown`** :
   - Erreurs inattendues
   - Problèmes réseau

### Format de réponse d'erreur

```json
{
  "query": "...",
  "results": [],
  "error": "Message d'erreur descriptif",
  "error_type": "search_unavailable" | "unknown"
}
```

## Logging & Observabilité

Chaque recherche est loggée dans le journal de l'execution agent :

```python
# Succès
"search_news succeeded | query='AI regulation' | results=12"

# Échec
"search_academic failed | query='quantum' | error=MCP unavailable"
```

## Utilisation par l'Interaction Agent

L'interaction agent peut maintenant déléguer des recherches spécialisées :

**Avant** (1 outil générique) :
```
User: "Find me news about Tesla"
→ search_web("Tesla news")
```

**Après** (outils spécialisés) :
```
User: "Find me news about Tesla"
→ search_news("Tesla")

User: "Research quantum computing"
→ research_topic("quantum computing", focus_areas=["applications", "challenges"])

User: "What's Apple working on?"
→ search_company("Apple", aspects=["products", "news"])
```

## Configuration Requise

Aucune configuration supplémentaire nécessaire ! Utilise l'infrastructure Composio/Exa existante :

```bash
# Variables d'environnement (déjà configurées)
COMPOSIO_EXA_MCP_URL=...
COMPOSIO_EXA_USER_ID=...
COMPOSIO_EXA_TOOL_NAME=search_web
```

## Tests

### Test Manuel

```python
from server.agents.execution_agent.tools.search import search_news, research_topic

# Test 1: Recherche d'actualités
result = search_news("artificial intelligence regulation", num_results=5)
print(f"Found {len(result['results'])} news articles")

# Test 2: Recherche approfondie
result = research_topic(
    "climate change",
    focus_areas=["impact", "solutions", "policy"]
)
print(f"Total results: {result['total_results']}")
```

### Vérification des Schémas

```python
from server.agents.execution_agent.tools.search import get_schemas

schemas = get_schemas()
print(f"Nombre d'outils de recherche: {len(schemas)}")
# Output: 5
```

## Performance

### Latence Attendue
- `search_web`: ~1-2s
- `search_news`: ~1-2s (filtrage domaines)
- `research_topic`: ~3-6s (recherches multiples)
- `search_company`: ~2-4s (par aspect)
- `search_academic`: ~1-2s (filtrage domaines)

### Limites de Résultats
- Maximum par recherche: 20 résultats
- `research_topic`: Distribue entre focus areas
- `search_company`: Multiplie par nombre d'aspects

## Évolutions Futures

### Améliorations Possibles

1. **Cache des Résultats** :
   ```python
   # Éviter les recherches identiques
   _SEARCH_CACHE: Dict[str, CachedResult] = {}
   ```

2. **Recherche Parallèle** :
   ```python
   # Pour research_topic et search_company
   async def _parallel_search(queries: List[str]) -> List[Results]
   ```

3. **Agrégation Intelligente** :
   ```python
   # Déduplication et ranking
   def _aggregate_results(results: List[Result]) -> List[Result]
   ```

4. **Recherche Temporelle** :
   ```python
   def search_news(
       query: str,
       time_range: Literal["day", "week", "month"] = "week"
   )
   ```

## Conclusion

L'agent de recherche suit exactement les mêmes patterns que Gmail :
- ✅ Séparation service/tools
- ✅ Thread safety (via service Exa)
- ✅ Logging & observabilité
- ✅ Gestion d'erreurs robuste
- ✅ Schémas OpenAI bien définis

Les 5 outils spécialisés permettent des recherches ciblées et efficaces, tout en réutilisant l'infrastructure Composio existante.

