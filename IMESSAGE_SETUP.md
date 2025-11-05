# iMessage Setup Guide for Alyn

Ce guide vous explique comment configurer Alyn pour qu'elle fonctionne via iMessage au lieu d'une interface web.

## Prérequis

1. **macOS** - iMessage ne fonctionne que sur Mac
2. **iMessage configuré** - Votre compte Apple connecté à iMessage
3. **Node.js** - Version 16 ou supérieure (`node --version`)
4. **Python 3.11+** - Avec votre environnement virtuel configuré

## Configuration en 3 étapes

### Étape 1 : Accorder l'accès au disque complet

C'est **CRUCIAL** pour que l'application puisse lire la base de données iMessage.

1. Ouvrez **Réglages Système** (System Settings)
2. Allez dans **Confidentialité et sécurité** → **Accès complet au disque** (Full Disk Access)
3. Cliquez sur le `+` et ajoutez :
   - Votre IDE (Cursor, VSCode, etc.) **OU**
   - L'application Terminal
4. **Redémarrez votre IDE/Terminal** après avoir accordé l'accès

### Étape 2 : Installer les dépendances

```bash
# Installer les dépendances Node.js
npm install

# Vérifier que tout est installé
npm list @photon-ai/imessage-kit
```

### Étape 3 : Démarrer le service iMessage

```bash
# Utiliser le script de démarrage
./start_imessage.sh

# OU démarrer manuellement
npm run watch
```

Vous devriez voir :
```
🚀 Alyn iMessage Watcher initialized
👀 Watching for iMessages (polling every 2000ms)...
📱 Send a message to this Mac via iMessage to test
```

## Test de l'installation

### 1. Tester la réception de messages

1. Démarrez le watcher : `./start_imessage.sh`
2. Envoyez-vous un iMessage depuis un autre appareil (iPhone, iPad, autre Mac)
3. Vérifiez la console - vous devriez voir :
   ```
   📨 New message from +1234567890:
      "Hello Alyn!"
   ✅ Message processed: Message from +1234567890 processed successfully
   ```

### 2. Tester l'envoi de messages

```bash
# Test d'envoi manuel
node server/services/imessage/send_message.js "+1234567890" "Test message"
```

Remplacez `+1234567890` par votre numéro de téléphone.

### 3. Test complet bout-en-bout

1. Démarrez le serveur FastAPI (si nécessaire) :
   ```bash
   python -m server.server
   ```

2. Démarrez le watcher iMessage :
   ```bash
   ./start_imessage.sh
   ```

3. Envoyez un message via iMessage :
   ```
   "What's the weather like today?"
   ```

4. Alyn devrait :
   - Recevoir votre message
   - Le traiter via l'interaction agent
   - Vous répondre dans iMessage

## Architecture

```
Vous (iMessage)
    ↓
imessage_watcher.js (détecte le message)
    ↓
imessage_bridge.py (transfert vers Alyn)
    ↓
InteractionAgentRuntime (traite avec LLM)
    ↓
send_message_to_user (détecte le contexte iMessage)
    ↓
imessage_sender.py → send_message.js
    ↓
Vous (réponse dans iMessage)
```

## Utilisation quotidienne

### Démarrer Alyn en mode iMessage

```bash
# Terminal 1 : Serveur FastAPI (pour les outils Gmail, Calendar, etc.)
python -m server.server

# Terminal 2 : Watcher iMessage
./start_imessage.sh
```

### Communiquer avec Alyn

Envoyez simplement un iMessage à votre Mac comme vous le feriez avec n'importe quel contact !

Exemples :
- "Check my emails"
- "What's on my calendar today?"
- "Send an email to john@example.com about the meeting"
- "Set a reminder for tomorrow at 9am"

## Mode hybride (HTTP + iMessage)

Vous pouvez utiliser **les deux** en même temps :
- Interface web/HTTP pour certains usages
- iMessage pour d'autres

Les deux partagent :
- La même conversation log
- Les mêmes agents d'exécution
- Les mêmes outils (Gmail, Calendar, etc.)

## Dépannage

### "Messages app is not running"

**Cause** : L'application Messages de macOS n'est pas ouverte.

**Solution** :
1. Ouvrez l'application **Messages** sur votre Mac
2. Assurez-vous d'être connecté avec votre compte Apple
3. Relancez le test ou le watcher

**Important** : L'application Messages doit rester ouverte en arrière-plan pour que l'intégration fonctionne.

### "Permission denied" lors de l'accès à la base iMessage

**Solution** : Accordez Full Disk Access à votre IDE/Terminal (voir Étape 1)

### "ENOENT: no such file or directory, open package.json"

**Cause** : Vous essayez d'exécuter `npm install` dans le mauvais répertoire.

**Solution** :
```bash
# Le package.json est dans .conductor/tokyo/, pas à la racine
cd .conductor/tokyo
npm install
```

### Les messages ne sont pas détectés

**Vérifications** :
1. L'application **Messages** est-elle ouverte ?
2. Le watcher est-il en cours d'exécution ? (`npm run watch`)
3. iMessage fonctionne-t-il normalement sur votre Mac ?
4. Avez-vous accordé Full Disk Access ?
5. Redémarrez le watcher après avoir modifié les permissions

### Les réponses ne sont pas envoyées

**Vérifications** :
1. L'application **Messages** est-elle ouverte ?
2. Vérifiez les logs dans la console du watcher
3. Testez l'envoi manuel : `node server/services/imessage/send_message.js "votre-numero" "test"`
4. Vérifiez que Node.js est bien installé : `node --version`

### Messages en double

Le watcher garde en mémoire les IDs de messages déjà traités. Si vous recevez des doublons :
- Redémarrez le watcher pour réinitialiser le cache

### Le bridge Python ne démarre pas

**Vérifications** :
1. L'environnement virtuel est activé : `source .venv/bin/activate`
2. Le chemin vers Python dans `imessage_watcher.js` est correct
3. Les imports Python fonctionnent : `python server/services/imessage/imessage_bridge.py --help`

## Fonctionnalités

### ✅ Fonctionnalités supportées
- Réception de messages texte
- Envoi de messages texte
- Détection automatique du contexte (HTTP vs iMessage)
- Tous les outils Alyn (Gmail, Calendar, etc.)
- Conversation log partagée
- Agents d'exécution en arrière-plan

### 🚧 Limitations actuelles
- Texte seulement (pas d'images/pièces jointes)
- Polling toutes les 2 secondes (pas temps réel)
- Un seul Mac à la fois
- Pas de conversations de groupe
- Pas de réactions/read receipts

### 🔮 Améliorations futures
- Support des images et pièces jointes
- Webhooks pour notifications temps réel
- Support multi-utilisateurs
- Conversations de groupe
- Réactions et indicateurs de frappe

## Fichiers importants

```
├── package.json                              # Dépendances Node.js
├── start_imessage.sh                         # Script de démarrage
├── server/services/imessage/
│   ├── README.md                            # Documentation détaillée
│   ├── imessage_watcher.js                  # Surveillance des messages
│   ├── imessage_bridge.py                   # Pont Python
│   ├── imessage_sender.py                   # Envoi via Python
│   ├── send_message.js                      # Envoi via Node.js
│   └── message_context.py                   # Contexte de routing
└── server/agents/interaction_agent/tools.py # Tools modifiés pour iMessage
```

## Support

Si vous rencontrez des problèmes :
1. Consultez la section Dépannage ci-dessus
2. Vérifiez les logs dans la console
3. Lisez `server/services/imessage/README.md` pour plus de détails

Enjoy using Alyn via iMessage! 🎉
