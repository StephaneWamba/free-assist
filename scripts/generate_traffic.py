"""
Génère du trafic réaliste sur l'API FreeAssist pour peupler le dashboard.
Usage: python scripts/generate_traffic.py
"""
import asyncio
import random
import httpx

API = "https://freeassist-api.fly.dev/api/v1/assistant/analyze"

TICKETS = [
    # Connectivité
    "Ma Freebox ne se connecte plus à internet depuis ce matin, le voyant DSL est rouge",
    "Je n'arrive pas à me connecter au wifi, mon téléphone ne trouve pas le réseau Free",
    "La connexion est très lente, je télécharge à 1 Mb/s alors que j'ai la fibre",
    "Le voyant Power de ma Freebox clignote en rouge, qu'est-ce que ça veut dire ?",
    "Internet coupe toutes les heures pendant quelques minutes, c'est insupportable",
    "Depuis l'orage d'hier, ma box ne remarche plus du tout",
    "Je n'arrive pas à accéder à mon espace client Free, j'ai un message d'erreur",
    "Ma TV Free ne reçoit plus les chaînes depuis ce matin",
    # Facturation
    "J'ai été prélevé deux fois ce mois-ci, je veux un remboursement",
    "Ma facture est beaucoup plus élevée que d'habitude, je ne comprends pas pourquoi",
    "Je veux contester un prélèvement qui n'a pas lieu d'être sur mon compte",
    "On m'a prélevé alors que j'avais résilié il y a 2 mois",
    "Je n'ai pas reçu ma facture de novembre, comment l'obtenir ?",
    "Il y a des frais de résiliation que je n'avais pas prévus sur ma dernière facture",
    "Je veux changer la date de prélèvement pour le 10 du mois",
    # Résiliation
    "Je veux résilier mon abonnement Freebox, comment faire ?",
    "Quels sont les délais pour résilier ? J'ai besoin de savoir rapidement",
    "Je déménage et Free n'est pas disponible dans ma nouvelle adresse, puis-je résilier sans frais ?",
    "J'ai résilié il y a 3 semaines mais je suis toujours prélevé",
    "Je veux annuler mon engagement et passer en sans engagement",
    "Combien ça coûte de résilier avant la fin de mon engagement de 24 mois ?",
    # Questions techniques
    "Comment configurer le contrôle parental sur ma Freebox ?",
    "Comment brancher ma Freebox Player en ethernet plutôt qu'en wifi ?",
    "Quelle est la différence entre la Freebox Ultra et la Freebox Pop ?",
    "Mon décodeur Free ne démarre plus, l'écran reste noir",
    "Comment accéder à l'interface d'administration de ma box ?",
    "Je veux changer le mot de passe de mon réseau wifi",
    "Comment brancher mon téléphone fixe sur la Freebox ?",
    # Offres
    "Quelles sont les offres disponibles pour la fibre optique ?",
    "Je veux passer à une offre supérieure, quels sont les tarifs ?",
    "Y a-t-il des promotions en ce moment pour les nouveaux abonnés ?",
    "Puis-je garder mon numéro de téléphone fixe si je change d'opérateur pour Free ?",
    "Quelle est la différence de prix entre la Freebox Pop et la Freebox Ultra ?",
]

async def send(client: httpx.AsyncClient, text: str, i: int) -> None:
    try:
        r = await client.post(API, json={"text": text}, timeout=60)
        status = r.status_code
        if status == 200:
            data = r.json()
            intent = data.get("intent", "?")
            ms = data.get("processing_ms", 0)
            print(f"[{i:02d}] OK {intent:30s} {ms:6.0f}ms")
        else:
            print(f"[{i:02d}] ERR HTTP {status}")
    except Exception as e:
        print(f"[{i:02d}] ERR {e}")

async def main():
    print(f"Envoi de {len(TICKETS)} requêtes vers {API}\n")
    async with httpx.AsyncClient() as client:
        # Warm-up
        print("Warm-up...")
        await send(client, TICKETS[0], 0)
        await asyncio.sleep(2)

        # Trafic par batch de 5 avec délai
        for i in range(0, len(TICKETS), 5):
            batch = TICKETS[i:i+5]
            tasks = [send(client, text, i+j+1) for j, text in enumerate(batch)]
            await asyncio.gather(*tasks)
            await asyncio.sleep(random.uniform(1.5, 3.0))

    print("\nTerminé — vérifiez le dashboard !")

if __name__ == "__main__":
    asyncio.run(main())
