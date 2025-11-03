# Analyse de l'implémentation Composio

## Architecture Composio pour Gmail

### 1. **Configuration** (`config.py`)
```python
# Variables d'environnement Composio
composio_api_key: Optional[str]                    # Clé API Composio
composio_gmail_auth_config_id: Optional[str]        # Config OAuth Gmail
composio_exa_mcp_url: Optional[str]                 # URL MCP pour recherche Exa
composio_exa_user_id: Optional[str]                 # User ID pour Exa
composio_exa_tool_name: str = "search_web"          # Nom de l'outil de recherche
```

### 2. **Service Gmail** (`services/gmail/client.py`)

#### Pattern Singleton Thread-Safe
```python
_CLIENT: Optional[Any] = None
_CLIENT_LOCK = threading.Lock()

def _get_composio_client():
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    with _CLIENT_LOCK:
        if _CLIENT is None:
            from composio import Composio
            _CLIENT = Composio(api_key=api_key) if api_key else Composio()
    return _CLIENT
```

#### Gestion des connexions OAuth
- `initiate_connect()` : Démarre le flux OAuth, retourne redirect_url
- `fetch_status()` : Vérifie le statut de connexion, récupère le profil
- `disconnect_account()` : Déconnecte et nettoie les caches

#### Exécution d'outils
```python
def execute_gmail_tool(
    tool_name: str,
    composio_user_id: str,
    *,
    arguments: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    client = _get_composio_client()
    result = client.client.tools.execute(
        tool_name,
        user_id=composio_user_id,
        arguments=prepared_arguments,
    )
    return _normalize_tool_response(result)
```

### 3. **Outils Gmail pour Execution Agent** (`agents/execution_agent/tools/gmail.py`)

#### Structure des outils
```python
# 1. Schémas OpenAI
_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "gmail_create_draft",
            "description": "...",
            "parameters": {...}
        }
    },
    ...
]

# 2. Fonctions d'implémentation
def gmail_create_draft(...) -> Dict[str, Any]:
    composio_user_id = get_active_gmail_user_id()
    if not composio_user_id:
        return {"error": "Gmail not connected..."}
    return _execute("GMAIL_CREATE_EMAIL_DRAFT", composio_user_id, arguments)

# 3. Registry builder
def build_registry(agent_name: str) -> Dict[str, Callable]:
    return {
        "gmail_create_draft": gmail_create_draft,
        ...
    }
```

### 4. **Service de Recherche Exa** (`services/search/exa.py`)

#### Communication via MCP (Model Context Protocol)
```python
async def _fetch_via_mcp(query, limit, include_domains, exclude_domains):
    target_url = settings.composio_exa_mcp_url + "?user_id=" + user_id

    async with streamablehttp_client(target_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tool_result = await session.call_tool(tool_name, arguments)
```

## Patterns Clés Identifiés

### 1. **Séparation des Responsabilités**
- **Services** : Gestion bas-niveau (client, auth, exécution)
- **Tools** : Interface haut-niveau pour les agents (schémas + fonctions)
- **Config** : Centralisation des variables d'environnement

### 2. **Thread Safety**
- Singleton avec double-checked locking
- Caches protégés par locks (`_PROFILE_CACHE_LOCK`, `_ACTIVE_USER_ID_LOCK`)

### 3. **Error Handling Robuste**
- Try-except à chaque niveau
- Normalisation des réponses (`_normalize_tool_response`)
- Logging structuré avec contexte

### 4. **User Context Management**
- `get_active_gmail_user_id()` : Récupère le user_id actif
- Cache des profils par user_id
- Validation systématique de la connexion

### 5. **Logging & Observability**
```python
_LOG_STORE.record_action(
    agent_name,
    description=f"{tool_name} succeeded | args={payload_str}"
)
```

## Recommandations pour l'Agent de Recherche

### Architecture Proposée

```
server/
├── services/
│   └── search/
│       ├── __init__.py
│       ├── composio_client.py   # Client Composio réutilisable
│       └── exa.py               # Déjà existe
│
├── agents/
│   └── execution_agent/
│       └── tools/
│           ├── search.py        # Outils de recherche
│           └── web_research.py  # Outils de recherche avancée
```

### Outils à Implémenter

1. **search_web** : Recherche web générale (déjà existe via Exa)
2. **search_news** : Recherche d'actualités
3. **research_topic** : Recherche approfondie sur un sujet
4. **search_company** : Recherche d'informations sur une entreprise
5. **search_person** : Recherche d'informations sur une personne

### Avantages de l'Approche Composio

✅ **Abstraction** : Pas besoin de gérer les API directement
✅ **Authentification** : Gérée par Composio
✅ **Rate Limiting** : Géré par Composio
✅ **Normalisation** : Réponses structurées
✅ **MCP** : Communication standardisée avec les outils externes

