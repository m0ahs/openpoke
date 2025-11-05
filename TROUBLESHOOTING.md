# Troubleshooting iMessage Integration

## Erreur : "NODE_MODULE_VERSION 137... requires NODE_MODULE_VERSION 115"

**Symptôme** :
```
_IMessageError: Failed to open database at /Users/.../Library/Messages/chat.db:
The module '.../better-sqlite3.node' was compiled against a different Node.js version
```

**Cause** : Le module natif `better-sqlite3` a été compilé pour une version différente de Node.js.

**Solution** :
```bash
npm rebuild better-sqlite3
```

**Solution permanente** : Utilisez toujours `./start_imessage.sh` qui fait automatiquement le rebuild.

## Erreur : "Messages app is not running"

**Symptôme** :
```
IMessageError: Messages app is not running [Recipient: +...]
```

**Cause** : L'application Messages de macOS n'est pas ouverte.

**Solution** :
```bash
open -a Messages
```

L'application doit rester ouverte en arrière-plan.

## Erreur : "Permission denied" / "Failed to open database"

**Cause** : Pas d'accès complet au disque (Full Disk Access).

**Solution** :
1. **Réglages Système** → **Confidentialité et sécurité** → **Accès complet au disque**
2. Ajoutez votre Terminal ou IDE
3. **Redémarrez** l'application après l'avoir ajoutée

## Les messages ne sont pas détectés

**Vérifications** :
1. ✅ L'application Messages est-elle ouverte ?
2. ✅ Le watcher est-il en cours d'exécution ?
3. ✅ Full Disk Access est-il accordé ?
4. ✅ Les messages que vous envoyez sont-ils **nouveaux** (pas avant le démarrage du watcher) ?

**Test** :
Le watcher ne traite que les messages reçus **après** son démarrage. Les anciens messages sont ignorés.

## Pas de réponse d'Alyn

**Vérifications** :
1. ✅ Le serveur FastAPI est-il en cours d'exécution ?
2. ✅ L'environnement Python (.venv) est-il activé ?
3. ✅ Les variables d'environnement (OPENROUTER_API_KEY, etc.) sont-elles configurées ?

**Logs** :
Regardez les logs du watcher - vous devriez voir :
```
📨 New message from +...:
   "votre message"
✅ Message from +... processed successfully
```

Si vous voyez seulement la première ligne sans la seconde, le bridge Python a échoué.

## Le bridge Python échoue

**Test manuel** :
```bash
.venv/bin/python server/services/imessage/imessage_bridge.py \
  --sender "+33612345678" \
  --text "test" \
  --timestamp "2025-01-01T12:00:00Z"
```

Si cela échoue, vérifiez :
- L'environnement Python est activé
- Les dépendances sont installées
- Les imports fonctionnent

## Trop de logs de debug

**Solution** : Désactiver le mode debug dans `imessage_watcher.js` :

Ligne 25-29 :
```javascript
this.sdk = new IMessageSDK({
  debug: false,  // Changez true en false
  concurrency: 5,
  timeout: 30000
});
```

Commentez aussi les `console.log` de debug aux lignes 82, 86, 92, 99.

## Rebuild automatique

Le script `./start_imessage.sh` fait automatiquement `npm rebuild better-sqlite3` à chaque démarrage pour éviter les problèmes de version Node.js.

Si vous utilisez `npm run watch` directement, vous devez faire le rebuild manuellement quand vous changez de version de Node.js.
