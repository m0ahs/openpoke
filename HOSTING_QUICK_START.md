# 🚀 Héberger Alyn en 5 minutes

## Solution la plus simple: Railway.app

### Étape 1: Préparer le code
```bash
git add .
git commit -m "Ready for deployment"
git push origin main
```

### Étape 2: Déployer sur Railway

1. **Allez sur https://railway.app**
2. **Cliquez sur "New Project" → "Deploy from GitHub repo"**
3. **Sélectionnez votre repo**

### Étape 3: Configurer le Backend

1. Railway crée automatiquement un service
2. **Renommez-le en "backend"**
3. **Settings → Variables**, ajoutez:
   ```
   OPENROUTER_API_KEY=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
   COMPOSIO_API_KEY=ak_lccaZmGAOY3FaXiCRJLg
   COMPOSIO_GMAIL_AUTH_CONFIG_ID=ac_-3cIgi-AWyJw
   ```

4. **Settings → Dockerfile Path**: `Dockerfile.backend`

5. **Storage → Add Volume**:
   - Mount Path: `/app/server/data`
   - Donnez-lui un nom: `alyn-data`

6. **Deploy!**

### Étape 4: Configurer le Frontend

1. **Cliquez sur "+ New" → "Service"**
2. **Choisissez le même repo**
3. **Renommez en "frontend"**
4. **Settings → Variables**, ajoutez:
   ```
   PY_SERVER_URL=https://votre-backend-url.railway.app
   ```
   (Copiez l'URL depuis le service backend)

5. **Settings → Dockerfile Path**: `Dockerfile.frontend`

6. **Deploy!**

### Étape 5: Obtenir votre URL

1. Dans le service "frontend"
2. **Settings → Networking → Generate Domain**
3. Vous obtenez: `https://alyn-xxxxx.railway.app`

### 🎉 C'est prêt!

Visitez votre URL et Alyn est accessible 24/7!

---

## Coût: ~$5-10/mois

Railway offre $5 de crédit gratuit par mois. Parfait pour un usage personnel.

---

## Besoin d'aide?

Consultez `DEPLOYMENT.md` pour plus d'options (Fly.io, VPS, etc.)

---

## Alternative ultra-rapide: Render.com

1. Allez sur https://render.com
2. New → Web Service
3. Connectez votre GitHub
4. Render détecte automatiquement les Dockerfiles
5. Configurez les mêmes variables d'environnement

Prix: $7/mois (backend) + Gratuit (frontend static)
