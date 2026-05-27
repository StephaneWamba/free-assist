"""
FreeAssist — Data Simulator
Generates realistic noisy French telecom support conversations.

Can use either built-in templates or GPT-augmented templates from augment_gpt.py.

Usage:
    # With built-in templates only
    python generate.py --n 2000 --output data/processed/train --split train

    # With GPT-augmented templates (recommended before fine-tuning)
    python generate.py --n 2000 --output data/processed/train --split train \\
        --templates-file data/simulator/augmented_templates.json

    # Generate train + val + test in one go
    python generate.py --all --templates-file data/simulator/augmented_templates.json
"""

from __future__ import annotations

import argparse
import json
import random
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator


# ---------------------------------------------------------------------------
# Domain constants
# ---------------------------------------------------------------------------

INTENTS = [
    "BOX_CONNECTIVITY",
    "BOX_REBOOT",
    "MOBILE_PORTABILITY",
    "BILLING_DISPUTE",
    "CONTRACT_CHANGE",
    "TECHNICAL_OUTAGE",
    "EQUIPMENT_RETURN",
    "SPEED_ISSUE",
    "CANCELLATION",
    "OTHER",
]

# Mirrors realistic telecom support distribution
INTENT_WEIGHTS = [0.20, 0.12, 0.08, 0.15, 0.07, 0.13, 0.05, 0.10, 0.06, 0.04]

AGENT_NAMES = ["Sophie", "Thomas", "Amina", "Lucas", "Fatou", "Kevin", "Nadia", "Romain"]

# ---------------------------------------------------------------------------
# Built-in fallback templates (used when no augmented file is provided)
# ---------------------------------------------------------------------------

_BUILTIN_TEMPLATES: dict[str, list[tuple[str, ...]]] = {
    "BOX_CONNECTIVITY": [
        (
            "Bonjour ma box free marche plus depuis ce matin, j'ai plus internet",
            "Bonjour ! Je suis désolé d'entendre cela. Depuis combien de temps exactement ?",
            "depuis 8h ce matin environ, les voyants clignotent en rouge",
            "D'accord. Le voyant rouge indique souvent un problème de synchronisation. Avez-vous essayé de redémarrer la box ?",
            "oui j'ai débranché et rebranché mais ça change rien",
            "Je vois. Je vais lancer un diagnostic à distance sur votre ligne. Pouvez-vous me donner votre numéro de ligne ou l'adresse de l'abonnement ?",
        ),
        (
            "salut, internet coupé depuis hier soir, très urgent pour le télétravail",
            "Bonjour, je comprends l'urgence. Votre connexion est coupée totalement ou intermittente ?",
            "completement coupée, aucun appareil arrive à se connecter meme en wifi",
            "Merci. Sur votre Freebox, quel est l'état des voyants lumineux en ce moment ?",
            "il y en a un rouge fixe et les autres sont eteints",
            "Le voyant rouge fixe signifie une perte de signal sur la ligne DSL ou fibre. Je vais effectuer un test de ligne de mon côté.",
        ),
        (
            "ma connexion marche pas, j'arrive pas à me connecter à internet",
            "Bonjour ! Vous parlez de votre connexion Freebox ou mobile ?",
            "freebox, je capte le wifi mais j'ai pas internet",
            "D'accord, le Wi-Fi est actif mais pas d'accès Internet. Avez-vous un message d'erreur sur votre navigateur ?",
            "oui ça dit DNS_PROBE_FINISHED_NO_INTERNET",
            "Ce type d'erreur peut venir des paramètres DNS ou d'une coupure réseau. Essayons d'abord un redémarrage complet de la box.",
        ),
    ],
    "BOX_REBOOT": [
        (
            "comment je fais pour redemarrer ma freebox ?",
            "Bonjour ! Vous souhaitez redémarrer votre Freebox Revolution, Pop ou Delta ?",
            "revolution je crois",
            "Pour la Freebox Revolution : maintenez le bouton marche/arrêt à l'arrière pendant 3 secondes, attendez 2 minutes le temps du redémarrage complet.",
            "ok merci j'essaie",
            "N'hésitez pas à me recontacter si le problème persiste après le redémarrage.",
        ),
        (
            "je veux faire un reset de ma box, comment proceder",
            "Bonjour ! Je vais vous guider. Attention : un reset d'usine efface tous vos paramètres personnalisés. Êtes-vous sûr de vouloir effectuer un reset complet ?",
            "oui c'est pour régler un problème de configuration",
            "D'accord. Sur votre Freebox, localisez le petit bouton reset (généralement avec une épingle). Maintenez-le enfoncé 10 secondes jusqu'à ce que les voyants clignotent.",
        ),
    ],
    "BILLING_DISPUTE": [
        (
            "bonjour j'ai été prélevé deux fois ce mois-ci c'est quoi ce bordel",
            "Bonjour, je comprends votre mécontentement et je m'en excuse. Pouvez-vous me confirmer les montants prélevés et les dates ?",
            "le 3 et le 17 du mois, deux fois 29,99€",
            "Je vois. Je vais examiner votre historique de facturation. Cela peut être lié à un changement de date de prélèvement lors d'une modification de votre offre.",
            "vous avez combien de temps ? parce que ça fait 2 semaines que j'attends",
            "Je comprends votre impatience. Je constate effectivement un doublon de prélèvement. Je vais initier le remboursement immédiatement, vous le recevrez sous 5 jours ouvrés.",
        ),
        (
            "ma facture est beaucoup plus élevée que d'habitude, je comprends pas",
            "Bonjour ! Je vais regarder cela. Quel est le montant habituel et le montant de cette facture ?",
            "d'habitude c'est 39 euros et là c'est 67 euros",
            "Je consulte votre facture... Je vois des frais de hors-forfait sur des appels vers l'étranger.",
            "ah oui j'ai appelé ma famille au maroc mais je pensais que c'était inclus",
            "Je comprends la confusion. Les appels vers le Maroc sont inclus uniquement vers les fixes. Les mobiles sont hors-forfait à 0,40€/min.",
        ),
    ],
    "MOBILE_PORTABILITY": [
        (
            "je veux garder mon numéro de portable en changeant d'opérateur pour venir chez free",
            "Bonjour et bienvenue ! Pour la portabilité, vous aurez besoin de votre RIO. Avez-vous ce code ?",
            "non comment je l'obtiens ?",
            "Appelez le 3179 (gratuit depuis votre mobile actuel), un serveur vocal vous communiquera votre RIO par SMS immédiatement.",
            "ok j'ai mon rio maintenant",
            "Parfait ! Lors de votre souscription sur free.fr, renseignez ce RIO dans le champ dédié. La portabilité prend généralement 3 jours ouvrés.",
        ),
    ],
    "CONTRACT_CHANGE": [
        (
            "je voudrais passer à une offre plus chère avec plus de débit",
            "Bonjour ! Je vais vous présenter les offres disponibles. Actuellement vous êtes sur quelle offre ?",
            "freebox pop à 29,99 par mois",
            "Très bien. La Freebox Ultra à 49,99€/mois offre jusqu'à 8 Gb/s en téléchargement et inclut les bouquets TV premium.",
            "oui mais ya des frais de mise en service ?",
            "Pour une migration depuis votre offre actuelle, les frais de mise en service sont offerts pendant notre promotion actuelle.",
        ),
    ],
    "TECHNICAL_OUTAGE": [
        (
            "ya une panne dans mon secteur ou c'est juste moi",
            "Bonjour ! Je consulte l'état de notre réseau. Pouvez-vous me donner votre code postal ?",
            "75013",
            "Je vois effectivement une perturbation signalée sur Paris 13ème depuis 10h30. Le rétablissement est prévu avant 14h.",
            "ok merci, et pour avoir un geste commercial vu que j'ai pas eu internet pendant 4h ?",
            "Tout à fait légitime. Un crédit d'un jour d'abonnement sera appliqué automatiquement sur votre prochaine facture.",
        ),
    ],
    "EQUIPMENT_RETURN": [
        (
            "j'ai resilié et je dois rendre ma freebox, comment je procede",
            "Bonjour. Suite à votre résiliation, vous devez retourner votre Freebox sous 15 jours. Avez-vous reçu le kit retour par email ?",
            "non j'ai rien recu",
            "Je vais vous renvoyer le kit retour par email. Il contient l'étiquette Colissimo prépayée.",
            "et si je rends pas je me prends une pénalité ?",
            "En cas de non-retour, des frais de non-restitution de 100€ à 250€ selon le modèle peuvent être facturés.",
        ),
    ],
    "SPEED_ISSUE": [
        (
            "mon débit est très lent depuis 3 jours, j'arrive meme pas à regarder une vidéo",
            "Bonjour ! Quel débit mesurez-vous actuellement ? Vous pouvez tester sur speedtest.net.",
            "j'ai fait le test, je reçois 8 mbps alors que j'ai la fibre à 1 giga",
            "Effectivement c'est anormal. Êtes-vous connecté en filaire ou en Wi-Fi lors du test ?",
            "en wifi",
            "Le Wi-Fi peut être perturbé. Essayez un test en filaire directement sur la box. Si le débit est correct en filaire, le problème vient du Wi-Fi.",
        ),
    ],
    "CANCELLATION": [
        (
            "je souhaite résilier mon abonnement freebox",
            "Bonjour, je suis désolé de vous entendre. Puis-je vous demander la raison de cette résiliation ?",
            "je déménage à l'étranger",
            "Je comprends. Pour une résiliation, nous avons besoin d'un préavis de 15 jours minimum. Avez-vous votre numéro de contrat ?",
            "c'est quoi le numéro de contrat",
            "Vous le trouvez sur votre facture mensuelle en haut à droite, ou dans votre espace client free.fr sous 'Mon compte'.",
        ),
    ],
    "OTHER": [
        (
            "bonjour je voulais juste savoir si free a un service client le dimanche",
            "Bonjour ! Oui, notre service client est disponible 7j/7 de 8h à 22h, y compris le dimanche.",
            "non merci c'était juste pour savoir",
            "Très bien ! N'hésitez pas à nous recontacter si besoin. Bonne journée !",
        ),
    ],
}

# ---------------------------------------------------------------------------
# Noise injection
# ---------------------------------------------------------------------------

_COMMON_TYPOS = {
    "bonjour": ["bonjoru", "bnjour", "bojour"],
    "connexion": ["conexion", "conection", "connction"],
    "problème": ["probleme", "problème", "problm"],
    "internet": ["internt", "interneet", "iternet"],
    "facture": ["factrue", "facutre"],
    "résiliation": ["resilition", "resiliation"],
    "freebox": ["frebox", "free box", "fre box"],
    "redémarrer": ["redemarrer", "redémarré", "rédémarrer"],
    "opérateur": ["operateur", "opérateur"],
    "abonnement": ["abonnment", "abonement"],
}

_ABBREVIATIONS = {
    "je": "j",
    "c'est": "c",
    "s'il vous plaît": "svp",
    "depuis": "dep",
    "merci": "mrc",
    "très": "tres",
    "il y a": "ya",
    "qu'est-ce que": "c quoi",
    "s'il vous plaît": "svp",
    "je ne": "j'n",
}


def _inject_noise(text: str, level: float = 0.35) -> str:
    """Apply realistic chat noise to a message — only applied to user turns."""
    if random.random() > level:
        return text

    ops = random.choices(
        ["typo", "lowercase", "no_punct", "abbreviation"],
        weights=[0.3, 0.4, 0.2, 0.1],
    )
    for op in ops:
        if op == "typo":
            for word, variants in _COMMON_TYPOS.items():
                if word in text.lower():
                    text = re.sub(word, random.choice(variants), text, flags=re.IGNORECASE, count=1)
        elif op == "lowercase":
            text = text.lower()
        elif op == "no_punct":
            text = text.rstrip(".!?")
        elif op == "abbreviation":
            for phrase, abbrev in _ABBREVIATIONS.items():
                if phrase in text.lower():
                    text = text.lower().replace(phrase, abbrev, 1)

    return text


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------


def load_augmented_templates(path: Path) -> dict[str, list[list[dict]]]:
    """Load GPT-augmented templates from augment_gpt.py output."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["intents"]  # {intent: [{turns: [{role, content}, ...]}, ...]}


def _builtin_as_augmented() -> dict[str, list[list[dict]]]:
    """Convert built-in tuple templates to the augmented format for uniform handling."""
    result: dict[str, list[list[dict]]] = {}
    for intent, templates in _BUILTIN_TEMPLATES.items():
        result[intent] = []
        for template in templates:
            turns = [
                {"role": "user" if i % 2 == 0 else "agent", "content": msg}
                for i, msg in enumerate(template)
            ]
            result[intent].append({"turns": turns})
    return result


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Turn:
    role: str
    content: str
    timestamp: str


@dataclass
class Conversation:
    id: str
    intent: str
    agent_name: str
    turns: list[Turn]
    created_at: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "intent": self.intent,
            "agent_name": self.agent_name,
            "turns": [asdict(t) for t in self.turns],
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


def _make_timestamp(base: datetime, offset_seconds: int) -> str:
    return (base + timedelta(seconds=offset_seconds)).isoformat()


def generate_conversation(intent: str, templates: dict[str, list[dict]]) -> Conversation:
    intent_templates = templates.get(intent, templates.get("OTHER", []))
    chosen = random.choice(intent_templates)
    raw_turns = chosen if isinstance(chosen, list) else chosen.get("turns", [])

    base_time = datetime.now() - timedelta(
        days=random.randint(0, 90),
        hours=random.randint(0, 12),
    )

    turns: list[Turn] = []
    for i, turn in enumerate(raw_turns):
        role = turn["role"]
        content = turn["content"]
        # Apply noise only to user messages
        if role == "user":
            content = _inject_noise(content, level=0.35)
        turns.append(
            Turn(
                role=role,
                content=content,
                timestamp=_make_timestamp(base_time, offset_seconds=i * random.randint(15, 120)),
            )
        )

    return Conversation(
        id=str(uuid.uuid4()),
        intent=intent,
        agent_name=random.choice(AGENT_NAMES),
        turns=turns,
        created_at=base_time.isoformat(),
        metadata={
            "channel": random.choice(["chat", "email", "phone_transcript"]),
            "resolved": random.random() > 0.15,
            "satisfaction_score": random.choice([None, 1, 2, 3, 4, 5]),
            "duration_seconds": len(turns) * random.randint(20, 90),
        },
    )


def generate_dataset(n: int, templates: dict[str, list[dict]]) -> Iterator[Conversation]:
    intents_pool = random.choices(INTENTS, weights=INTENT_WEIGHTS, k=n)
    for intent in intents_pool:
        yield generate_conversation(intent, templates)


# ---------------------------------------------------------------------------
# Save helpers
# ---------------------------------------------------------------------------


def save_split(conversations: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    # Full conversations (for RAG / generative fine-tuning)
    with open(output_dir / "conversations.jsonl", "w", encoding="utf-8") as f:
        for conv in conversations:
            f.write(json.dumps(conv, ensure_ascii=False) + "\n")

    # Intent classification format (text = first user message)
    with open(output_dir / "intent_classification.jsonl", "w", encoding="utf-8") as f:
        for conv in conversations:
            first_user = next((t["content"] for t in conv["turns"] if t["role"] == "user"), "")
            record = {
                "id": conv["id"],
                "text": first_user,
                "label": conv["intent"],
                "label_id": INTENTS.index(conv["intent"]),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def print_distribution(conversations: list[dict], n: int) -> None:
    from collections import Counter
    counts = Counter(c["intent"] for c in conversations)
    print("\nIntent distribution:")
    for intent in INTENTS:
        count = counts.get(intent, 0)
        bar = "█" * (count * 40 // n)
        print(f"  {intent:<25} {count:>5}  {bar}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="FreeAssist — Conversation Data Generator")
    parser.add_argument("--n", type=int, default=2000, help="Number of conversations to generate")
    parser.add_argument("--output", type=str, default="data/processed/train", help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--templates-file", type=str, default=None, help="Path to augmented_templates.json")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate train (2000) + val (300) + test (300) in one go",
    )
    args = parser.parse_args()

    # Load templates
    if args.templates_file and Path(args.templates_file).exists():
        print(f"Using augmented templates from {args.templates_file}")
        templates = load_augmented_templates(Path(args.templates_file))
    else:
        print("Using built-in templates (run augment_gpt.py first for better quality)")
        templates = _builtin_as_augmented()

    if args.all:
        # -----------------------------------------------------------------------
        # Template-level split: each split sees DIFFERENT source templates so
        # F1 measures true generalisation, not pattern memorisation.
        #
        # With 8 templates per intent:
        #   train → templates 0-5  (75 %)
        #   val   → template  6    (12.5 %)
        #   test  → template  7    (12.5 %) — never seen during training
        # -----------------------------------------------------------------------
        def _slice_templates(
            all_t: dict[str, list[dict]], start: int, end: int | None
        ) -> dict[str, list[dict]]:
            sliced: dict[str, list[dict]] = {}
            for intent, tpls in all_t.items():
                subset = tpls[start:end]
                # Fall back to all templates if the slice is empty (few-template intents)
                sliced[intent] = subset if subset else tpls
            return sliced

        n_templates = min(len(v) for v in templates.values())
        train_end = max(1, int(n_templates * 0.75))
        val_end   = max(train_end + 1, int(n_templates * 0.875))

        print(f"\nTemplate-level split (total per intent: {n_templates}):")
        print(f"  train → templates [0:{train_end}]  ({train_end} templates)")
        print(f"  val   → templates [{train_end}:{val_end}]  ({val_end - train_end} template(s))")
        print(f"  test  → templates [{val_end}:end]  ({n_templates - val_end} template(s))")

        splits = [
            ("data/processed/train", 2000, 42,  _slice_templates(templates, 0, train_end)),
            ("data/processed/val",   300,  99,  _slice_templates(templates, train_end, val_end)),
            ("data/processed/test",  300, 123,  _slice_templates(templates, val_end, None)),
        ]
        for output_dir, n, seed, split_templates in splits:
            random.seed(seed)
            print(f"\nGenerating {n} conversations → {output_dir}")
            convs = [c.to_dict() for c in generate_dataset(n, split_templates)]
            save_split(convs, Path(output_dir))
            print_distribution(convs, n)
            print(f"✓ Saved {n} conversations to {output_dir}/")
    else:
        random.seed(args.seed)
        print(f"Generating {args.n} conversations → {args.output}")
        convs = [c.to_dict() for c in generate_dataset(args.n, templates)]
        save_split(convs, Path(args.output))
        print_distribution(convs, args.n)
        print(f"\n✓ Saved {args.n} conversations to {args.output}/")


if __name__ == "__main__":
    main()
