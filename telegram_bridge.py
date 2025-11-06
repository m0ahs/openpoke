import argparse
import sys
import os

# Ajoute le répertoire parent au path pour que les imports absolus depuis server fonctionnent
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Utilise des imports absolus depuis server pour éviter les problèmes d'imports relatifs
from server.agents.interaction_agent import InteractionAgentRuntime
import asyncio

def main():
    parser = argparse.ArgumentParser(description='Bridge Telegram messages to backend.')
    parser.add_argument('--sender', type=str, required=True)
    parser.add_argument('--text', type=str, required=True)
    parser.add_argument('--timestamp', type=str, required=False)
    args = parser.parse_args()

    # Appelle la logique backend pour traiter le message et générer la réponse
    async def run():
        try:
            runtime = InteractionAgentRuntime()
            result = await runtime.execute(user_message=args.text)

            # Affiche la réponse pour le watcher Telegram
            if result.success and result.response:
                # Réponse générée avec succès
                print(result.response)
                sys.exit(0)  # Succès : code de sortie 0

            if not result.success:
                # Erreur lors du traitement
                error_msg = result.error or "Une erreur s'est produite"
                print(f"Erreur: {error_msg}", file=sys.stderr)
                sys.exit(1)  # Échec : code de sortie 1

            # Cas: succès mais aucune réponse générée (duplicate detector, outil 'wait', etc.)
            # Pour Telegram, renvoyer un message explicite plutôt que rien.
            fallback = (
                "Je n'ai pas généré de réponse pour ce message. "
                "Peut-être que c'était un doublon ou qu'un outil silencieux a été utilisé. "
                "Réessaie si besoin."
            )
            print(fallback)
            sys.exit(0)
        except Exception as e:
            import traceback
            traceback.print_exc(file=sys.stderr)
            sys.exit(1)

    asyncio.run(run())

if __name__ == '__main__':
    main()
