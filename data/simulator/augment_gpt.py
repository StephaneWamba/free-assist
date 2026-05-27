"""
FreeAssist — GPT-4o-mini Data Augmentation

Generates N diverse French telecom support conversation variants per intent
using GPT-4o-mini, with parallel intent processing for speed.

Batch size is fixed at 10 variants per API call (~4K tokens output, safe under 16K limit).
All 10 intents are processed in parallel via ThreadPoolExecutor.

Output: data/simulator/augmented_templates.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI

BATCH_SIZE = 10  # variants per API call — ~4K tokens output, safe under 16K limit

INTENTS: dict[str, str] = {
    "BOX_CONNECTIVITY": "Le client a perdu sa connexion internet via sa Freebox (voyants, DNS, coupure totale ou partielle)",
    "BOX_REBOOT": "Le client veut redémarrer ou réinitialiser sa Freebox (reset usine, reboot simple)",
    "MOBILE_PORTABILITY": "Le client veut conserver son numéro mobile en venant chez Free (RIO, délais, procédure)",
    "BILLING_DISPUTE": "Le client conteste une facture (doublon de prélèvement, montant anormal, frais inattendus)",
    "CONTRACT_CHANGE": "Le client veut changer d'offre (upgrade, downgrade, options TV, migration)",
    "TECHNICAL_OUTAGE": "Le client signale une panne dans son secteur ou demande un geste commercial suite à une coupure",
    "EQUIPMENT_RETURN": "Le client doit rendre sa Freebox suite à une résiliation (délais, kit retour, pénalités)",
    "SPEED_ISSUE": "Le client se plaint d'un débit insuffisant (fibre lente, WiFi faible, test de débit)",
    "CANCELLATION": "Le client veut résilier son abonnement Freebox ou mobile (délai de préavis, procédure, motif)",
    "OTHER": "Demande générale ne rentrant pas dans les catégories ci-dessus (horaires, informations générales)",
}

GENERATION_PROMPT = """\
Tu es un générateur de données d'entraînement pour un modèle NLP de support client Free (opérateur télécom français).

Génère {n} conversations DISTINCTES et RÉALISTES de support client pour l'intention : **{intent}**
Description : {description}

Contraintes STRICTES :
1. Chaque conversation doit être DIFFÉRENTE (situation, vocabulaire, ton, longueur)
2. Utilise du français naturel, parlé, avec des imperfections : fautes de frappe, abréviations SMS, majuscules manquantes, ponctuation absente
3. 2 à 5 tours de parole (user/agent alternés, user en premier)
4. Le premier message user doit clairement signaler l'intention SANS utiliser son nom exact
5. Les réponses agent doivent être professionnelles, empathiques, et donner des étapes concrètes
6. Varie : le niveau d'urgence, le degré d'énervement, l'ancienneté client, le modèle de box (Revolution/Pop/Delta/Ultra), la région

Réponds UNIQUEMENT en JSON avec ce format exact :
{{
  "intent": "{intent}",
  "conversations": [
    {{
      "turns": [
        {{"role": "user", "content": "..."}},
        {{"role": "agent", "content": "..."}},
        ...
      ]
    }},
    ...
  ]
}}

Génère exactement {n} conversations."""


def _call_once(client: OpenAI, intent: str, description: str, n: int, retries: int = 3) -> list[dict]:
    prompt = GENERATION_PROMPT.format(intent=intent, description=description, n=n)
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=1.0,
                max_tokens=6000,
            )
            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)
            convs = data.get("conversations", [])
            if convs:
                return convs  # accept whatever we got — accumulation handles the total
            print(f"  [!] {intent}: empty response, retry {attempt+1}", flush=True)
            time.sleep(2)
        except Exception as exc:
            print(f"  [!] {intent}: attempt {attempt+1} failed: {exc}", flush=True)
            time.sleep(3 * (attempt + 1))
    return []


def generate_intent(client: OpenAI, intent: str, description: str, variants: int) -> tuple[str, list[dict]]:
    conversations: list[dict] = []
    n_batches = -(-variants // BATCH_SIZE)
    print(f"[{intent}] starting — {n_batches} batches of {BATCH_SIZE}", flush=True)

    for i in range(n_batches):
        remaining = variants - len(conversations)
        to_gen = min(BATCH_SIZE, remaining)
        batch = _call_once(client, intent, description, to_gen)
        conversations.extend(batch)
        print(f"[{intent}] batch {i+1}/{n_batches} done — {len(conversations)}/{variants}", flush=True)
        if len(conversations) >= variants:
            break

    print(f"[{intent}] DONE — {len(conversations)} conversations", flush=True)
    return intent, conversations[:variants]


def augment(api_key: str, variants: int, dry_run: bool, output: Path) -> None:
    if dry_run:
        n_batches = -(-variants // BATCH_SIZE)
        total_calls = len(INTENTS) * n_batches
        estimated_tokens = total_calls * BATCH_SIZE * 400
        print(f"[DRY RUN] {variants} variants × {len(INTENTS)} intents = {variants * len(INTENTS)} conversations")
        print(f"  {total_calls} API calls ({n_batches} batches/intent), ~{estimated_tokens:,} tokens")
        print(f"  Estimated cost: ~${estimated_tokens / 1_000_000 * 0.60:.2f}")
        print(f"  Parallel: all {len(INTENTS)} intents at once → ~{n_batches * 5}s total")
        return

    client = OpenAI(api_key=api_key)
    all_templates: dict[str, list[dict]] = {}

    print(f"Generating {variants} variants for {len(INTENTS)} intents in parallel...", flush=True)

    with ThreadPoolExecutor(max_workers=len(INTENTS)) as pool:
        futures = {
            pool.submit(generate_intent, client, intent, desc, variants): intent
            for intent, desc in INTENTS.items()
        }
        for future in as_completed(futures):
            intent, convs = future.result()
            all_templates[intent] = convs

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"intents": all_templates, "variants_per_intent": variants}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    total = sum(len(v) for v in all_templates.values())
    print(f"\n✓ Saved {total} conversations to {output}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY"))
    parser.add_argument("--variants", type=int, default=100)
    parser.add_argument("--output", default="data/simulator/augmented_templates.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.api_key and not args.dry_run:
        print("ERROR: --api-key or OPENAI_API_KEY required", file=sys.stderr)
        sys.exit(1)

    augment(
        api_key=args.api_key or "",
        variants=args.variants,
        dry_run=args.dry_run,
        output=Path(args.output),
    )


if __name__ == "__main__":
    main()
