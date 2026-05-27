# Procédure — Problème de Connectivité Freebox

## Diagnostic initial

### Voyants lumineux — signification

| Voyant | État | Signification |
|---|---|---|
| Power | Vert fixe | Box alimentée normalement |
| Power | Rouge fixe | Problème matériel |
| DSL/Fibre | Vert fixe | Ligne synchronisée |
| DSL/Fibre | Rouge clignotant | Pas de signal sur la ligne |
| DSL/Fibre | Orange | Synchronisation en cours |
| Wi-Fi | Vert | Wi-Fi actif |
| Wi-Fi | Éteint | Wi-Fi désactivé |

## Procédure de résolution étape par étape

### Étape 1 — Redémarrage simple
1. Appuyer sur le bouton marche/arrêt à l'arrière de la box
2. Attendre 30 secondes
3. Rallumer
4. Patienter 3 à 5 minutes pour la reconnexion complète

### Étape 2 — Vérification câblage
- Vérifier que le câble RJ11 (DSL) ou câble fibre est correctement branché
- S'assurer qu'aucun câble n'est plié ou endommagé
- Tester avec un câble de remplacement si disponible

### Étape 3 — Test de ligne à distance
L'agent peut lancer un diagnostic à distance depuis la console d'administration :
- Outil : DiagLine Pro (accès interne Free)
- Temps de diagnostic : 2 à 3 minutes
- Résultats : atténuation, rapport signal/bruit, erreurs de synchronisation

### Étape 4 — Réinitialisation aux paramètres d'usine
**Attention** : efface tous les paramètres personnalisés.
1. Localiser le bouton RESET (petite encoche)
2. Maintenir enfoncé avec un trombone pendant 10 secondes
3. La box redémarre automatiquement (5 à 10 minutes)

### Étape 5 — Escalade technique
Si aucune des étapes précédentes ne résout le problème :
- Créer un ticket d'intervention technique
- Délai d'intervention : 48-72h ouvrées
- Le client sera contacté pour convenir d'un rendez-vous

## Codes d'erreur fréquents

| Code | Signification | Action |
|---|---|---|
| ERR_DSL_001 | Pas de porteuse DSL | Vérifier câble, contacter FAI amont |
| ERR_SYNC_002 | Synchronisation échouée | Réinitialisation paramètres DSL |
| ERR_PPP_003 | Authentification PPP échouée | Vérifier identifiants, reset box |
| ERR_DHCP_004 | Pas d'adresse IP | Redémarrage box et modem |

## Escalade

- **Niveau 1** : Agent support (résolution téléphone/chat)
- **Niveau 2** : Équipe technique (diagnostic ligne avancé)
- **Niveau 3** : Technicien terrain (intervention physique)

## Notes importantes

- Ne jamais promettre un délai d'intervention ferme sans vérification disponibilité
- Toujours vérifier les incidents en cours sur le secteur avant tout diagnostic
- Proposer systématiquement un geste commercial si la coupure dépasse 4h
