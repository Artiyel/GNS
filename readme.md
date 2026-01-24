# Projet d'automatisation de configuration réseau 

Ce projet automatise la génération de fichiers de configuration pour routeurs Cisco (format `.cfg`) à partir d'un fichier d'intention JSON. Il gère l'adressage IPv6, les protocoles IGP (RIPng, OSPFv3) et les politiques BGP avancées avec les communautés.

## 1. Structure du Projet

* **`script.py`** : Point d'entrée principal. Il charge l'intention, calcule le plan d'adressage et génère la base des fichiers de configuration.
* **`intent.json`** : Fichier source décrivant la topologie, les AS, les interfaces et les types de relations eBGP.
* **`bgp_routing_communities.py`** : Module gérant la configuration BGP, incluant le marquage par communautés et les politiques de `local-preference`.
* **`ospf_routing.py` / `rip_routing.py`** : Modules dédiés à l'activation et à la configuration des protocoles de routage internes.
* **`config/`** : Répertoire de sortie contenant les fichiers `startup-config.cfg` générés.

---

## 2. Fonctionnalités Implémentées

### Adressage Automatique
* **Loopback 0** : Assignée sous la forme `2001:DB8:X::1/128` (X étant l'ID du routeur).
* **Interfaces Physiques** : Calcul automatique des préfixes `/64` pour les liaisons internes et inter-AS.

### Routage Interne (IGP)
* **OSPFv3** : Configuration des aires et des Router-IDs basés sur l'ID du routeur.
* **RIPng** : Activation sur les interfaces et redistribution des routes connectées et BGP.
* **Redistribution** : Les routes BGP sont réinjectées dans l'IGP pour assurer la connectivité globale au sein de l'AS.

### Politiques BGP (Communities & Local-Pref)
Le projet implémente une politique de routage intelligente basée sur les communautés BGP :
* **Tagging (Marquage)** : Les routes entrantes reçoivent un tag selon leur provenance : Client (`AS:100`), Peer (`AS:200`) ou Provider (`AS:300`).
* **Hiérarchie Économique** : La `local-preference` est ajustée pour préférer les chemins les moins coûteux : **Client (200) > Peer (150) > Provider (100)**.
* **Sécurité du Transit** : Utilisation de `route-maps` pour garantir que seules les routes de vos clients (et vos propres réseaux) sont exportées vers vos fournisseurs et pairs.



---

## 3. Utilisation

### Pré-requis
* Python.
* Un projet GNS3 configuré avec des routeurs Cisco supportant l'IPv6.

### Étapes de génération
1.  Configurez votre topologie dans le fichier `intent.json`.
2.  Lancez la génération des configurations :
    ```bash
    python script.py
    ```
3.  Le script va automatiquement :
    * Nettoyer et remplir le dossier `/config`.
    * Calculer les adresses et générer les fichiers `.cfg` pour chaque routeur.
    * Déployer les fichiers directement dans le dossier `dynamips` de GNS3 via la fonction `drag_and_drop`.

---

## 4. Utilisation

Ouvrez le projet GNS3 correspondant à votre fichier `intent.json` et allumez les routeurs. 

---
**Auteurs** : Camille Sarraméa, Quentin Zimmer, Martin Bonnard, Wassim Jahid