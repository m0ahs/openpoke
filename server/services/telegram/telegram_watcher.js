// Telegram Watcher for Seline
// Remplace iMessage par Telegram pour la communication avec le backend Python

import TelegramBot from 'node-telegram-bot-api';
import { spawn } from 'child_process';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

dotenv.config();
// Gestion de __dirname compatible ES module
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const TELEGRAM_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const PYTHON_BRIDGE_PATH = join(__dirname, '../../../telegram_bridge.py');
const VENV_PYTHON = join(__dirname, '../../../.venv/bin/python');
const CHAT_ID = process.env.TELEGRAM_CHAT_ID; // à définir dans .env

const bot = new TelegramBot(TELEGRAM_TOKEN, { polling: true });

console.log('🚀 Seline Telegram Watcher initialisé');

bot.on('message', async (msg) => {
  const chatId = msg.chat.id;
  const text = msg.text;
  console.log(`📨 Message Telegram reçu: ${text}`);

  // Démarre l'indicateur "typing" immédiatement
  let typingInterval = null;
  const startTyping = () => {
    bot.sendChatAction(chatId, 'typing');
    // Renouvelle l'indicateur toutes les 4 secondes (l'indicateur dure 5s max)
    typingInterval = setInterval(() => {
      bot.sendChatAction(chatId, 'typing');
    }, 4000);
  };

  const stopTyping = () => {
    if (typingInterval) {
      clearInterval(typingInterval);
      typingInterval = null;
    }
  };

  startTyping();

  // Transmet au backend Python en tant que module
  const pythonProcess = spawn(VENV_PYTHON, [
    PYTHON_BRIDGE_PATH,
    '--sender', chatId,
    '--text', text,
    '--timestamp', new Date().toISOString()
  ], {
    env: { ...process.env }
  });

  let stdout = '';
  let stderr = '';
  let processEnded = false;

  // Timeout de 2 minutes (120 secondes) pour éviter que le processus bloque indéfiniment
  const TIMEOUT_MS = 120000;
  const timeoutId = setTimeout(() => {
    if (!processEnded) {
      processEnded = true;
      stopTyping();
      pythonProcess.kill('SIGTERM'); // Tente un arrêt propre
      
      setTimeout(() => {
        if (!pythonProcess.killed) {
          pythonProcess.kill('SIGKILL'); // Force l'arrêt si nécessaire
        }
      }, 5000);
      
      console.error('⏱️  Timeout: le processus Python a pris plus de 2 minutes');
      bot.sendMessage(chatId, 'Désolé, le traitement a pris trop de temps. Réessaie avec un message plus court ou reformulé.', {
        disable_notification: false
      });
    }
  }, TIMEOUT_MS);

  pythonProcess.stdout.on('data', (data) => {
    stdout += data.toString();
  });

  pythonProcess.stderr.on('data', (data) => {
    // Les logs Python vont vers stderr, on les accumule pour vérification
    stderr += data.toString();
  });

  pythonProcess.on('close', (code) => {
    if (processEnded) return; // Déjà géré par le timeout
    
    processEnded = true;
    clearTimeout(timeoutId);
    stopTyping(); // Arrête l'indicateur typing
    
    const response = stdout.trim();
    // Ne considère comme erreur que les vraies erreurs (traceback, exceptions)
    // Les logs INFO/WARNING dans stderr ne sont pas des erreurs
    const hasTraceback = stderr.includes('Traceback') || 
                        stderr.includes('File "') || 
                        stderr.includes('Exception:') ||
                        (stderr.includes('Error:') && stderr.includes('at '));
    const isRealError = code !== 0 && hasTraceback;
    
    if (isRealError) {
      // Vraie erreur : on l'affiche et on informe l'utilisateur
      console.error(`❌ Erreur Python (code ${code}):`, stderr.substring(0, 500) || '(aucun détail)');
      bot.sendMessage(chatId, 'Désolé, une erreur s\'est produite lors du traitement de ton message.', {
        disable_notification: false // Force la notification même en cas d'erreur
      });
    } else if (response !== '' && !response.startsWith('Erreur:')) {
      // Succès : on envoie la réponse avec notification
      bot.sendMessage(chatId, response, {
        disable_notification: false // Force la notification
      });
      console.log(`✅ Réponse envoyée sur Telegram (${response.length} caractères)`);
    } else if (response.startsWith('Erreur:')) {
      // Erreur dans la réponse (mais pas de traceback)
      const errorMsg = response.replace('Erreur: ', '');
      bot.sendMessage(chatId, `⚠️ ${errorMsg}`, {
        disable_notification: false
      });
      console.log(`⚠️ Erreur dans la réponse: ${errorMsg}`);
    } else {
      // Aucune réponse mais pas d'erreur (cas : duplicata détecté, tool wait utilisé, etc.)
      const responsePreview = response ? response.substring(0, 50) : '(vide)';
      console.log(`⚠️  Aucune réponse générée (code: ${code}, stdout: "${responsePreview}", stderr length: ${stderr.length})`);
      // Informe l'utilisateur qu'il n'y a pas eu de réponse
      bot.sendMessage(chatId, 'Je n\'ai pas généré de réponse pour ce message. Peut-être que c\'était un doublon ou que j\'ai utilisé un outil silencieux. Réessaie si besoin.', {
        disable_notification: false
      });
    }
  });

  pythonProcess.on('error', (err) => {
    if (processEnded) return;
    processEnded = true;
    clearTimeout(timeoutId);
    stopTyping();
    console.error('❌ Erreur lors du lancement du processus Python:', err);
    bot.sendMessage(chatId, 'Désolé, impossible de lancer le traitement de ton message.', {
      disable_notification: false
    });
  });
});

// Arrêt propre
process.on('SIGINT', () => {
        // PYTHON_BRIDGE_PATH, // Suppression de la référence à iMessage
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\n\n👋 Arrêt du Telegram Watcher...');
  process.exit(0);
});
