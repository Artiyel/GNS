 

import json

with open('intent.json', 'r') as file:
    routing_data = json.load(file)

def writeBGPconfig(data):

    # On crée un dict pour trouver l'AS d'un routeur rapidement
    router_to_as = {}
    for as_id, as_info in data["AS"].items():
        for r in as_info["routers"]:
            router_to_as[r] = as_id

    # On parcourt tous les routeurs 
    for r_name, as_id in router_to_as.items():
        r_info = data["AS"][as_id]["routers"][r_name]
        path = f"config/R{r_name[1:]}_i{r_name[1:]}_startup-config.cfg"

        with open(path, "r") as f:
            config = f.readlines()

        config_lines = []
        neighbors = []
        i = 0

        while i < len(config): # On parcourt toutes les lignes de config
            
            # on réecrit ce qu'il y avait avant dans le fichier config
            config_lines.append(config[i])

            if (
                config[i] == "!\n"
                and config[i+1] == "!\n"
                and i + 2 < len(config)
                and config[i+2] == "ip forward-protocol nd\n"
            ):
                
                
                # BGP
                config_lines.extend([
                    f"router bgp {as_id}\n",
                    f" bgp router-id {r_name[1:]}.{r_name[1:]}.{r_name[1:]}.{r_name[1:]}\n",
                    " bgp log-neighbor-changes\n",
                    " no bgp default ipv4-unicast\n"
                ])

                
                # On détecte les routeurs de bordure
                # --> eBGP sur les interfaces de bordure
                border_routers = []
                for int_info in r_info["interfaces"].values():
                    neighbor = int_info.get("ngbr")
                    neighbor_as = router_to_as.get(neighbor)
                    if neighbor_as and neighbor_as != as_id: # Si les routeurs ne sont pas dans le même AS
                        border_routers.append(neighbor_as)

                        as_type = data["AS"][as_id]["ngbr_AS"][neighbor_as] # customer ou peer ou provider
                        remote_ip = None
                        for n_int in data["AS"][neighbor_as]["routers"][neighbor]["interfaces"].values(): # Pour toutes les interfaces du voisin
                            if n_int.get("ngbr") == r_name: # Si on est son voisin sur cette interface
                                remote_ip = n_int["ipv6"].split("/")[0] # on note son ip

                        if remote_ip: # on crée un dico des infos sur ce voisin hors de notre AS
                            neighbors.append({
                                "ip": remote_ip,
                                "type": as_type,
                                "remote_as": neighbor_as,
                                "ebgp": True
                            })

                        config_lines.extend([ # On ajoute à la configuration : 
                            f" neighbor {remote_ip} remote-as {neighbor_as}\n",
                            f" neighbor {remote_ip} description {as_type.upper()}-{neighbor}-AS{neighbor_as}\n", # pour les communities
                        ])
                

                # iBGP (loopbacks)
                for other_r, other_info in data["AS"][as_id]["routers"].items(): # pour tous les routeurs de notre AS
                    if other_r != r_name: # si le routeur n'est pas le notre
                        if "Loopback0" in other_info["interfaces"]: 
                            loop_ip = other_info["interfaces"]["Loopback0"]["ipv6"].split("/")[0] # on garde son adresse de loopback
                            neighbors.append({ # on garde ses infos 
                                "ip": loop_ip,
                                "ebgp": False
                            })
                            
                            config_lines.extend([ # on le définit comme voisin pour le full-mesh
                                f" neighbor {loop_ip} remote-as {as_id}\n",
                                f" neighbor {loop_ip} update-source Loopback0\n",
                            ])


                
                # address-family ipv6
                config_lines.extend(["!\n",
                    " address-family ipv6\n",
                ])
              

                # Utilisation d'un set pour éviter d'annoncer deux fois le même réseau
                # (par exemple si deux interfaces sont sur le même segment)
                networks = set()

                for int_info in r_info["interfaces"].values(): # pour chaque interface du routeur 
                    if "ipv6" in int_info:
                        prefix = ":".join(int_info["ipv6"].split(":")[:3]) + "::/64" # on prend son préfixe
                        networks.add(prefix) # on l'ajoute aux réseaux connus

                # On écrit les commandes network dans la config
                for net in sorted(networks):
                    config_lines.append(f"  network {net}\n") # on annonce les networks
                    config_lines.append(f"  network {net} route-map TAG-SELF\n") # permet de taguer le préfixe dès qu'il entre dans le processus BGP (taggué au même niveau qu'un client plus tard)


                for n in neighbors:
                    config_lines.append(f"  neighbor {n['ip']} activate\n") # pour chaque neighbor, on l'active avec son ip
                    config_lines.append(f"  neighbor {n['ip']} send-community\n") # Pour que les tags soient propagés en iBGP

                    if n.get("ebgp"): # si on communique avec le voisin en ebgp
                        
                        if n.get("type") == "customer":
                            # Si c'est mon client : je lui envoie tout 
                            config_lines.append(f"  neighbor {n['ip']} route-map FROM-CUSTOMER-IN in\n")
                            
                            
                        elif n.get("type") == "provider":
                            # Si c'est mon provider : je lui envoie que mes routes clients
                            config_lines.append(f"  neighbor {n['ip']} route-map TO-PROVIDER-OUT out\n")
                            # Je baisse la priorité de ses routes à 100
                            config_lines.append(f"  neighbor {n['ip']} route-map FROM-PROVIDER-IN in\n")

                    else:
                        # iBGP 
                        # Je lis les tags posés par mes routeurs de bordure
                        config_lines.append(f"  neighbor {n['ip']} route-map SET-LOCAL-PREF in\n")

                config_lines.append(" exit-address-family\n!\n")
                
                # communautés :
                config_lines.extend([
                    f"ip community-list standard CUSTOMER permit {as_id}:100\n",
                    f"ip community-list standard PEER permit {as_id}:200\n",
                    f"ip community-list standard PROVIDER permit {as_id}:300\n!\n"
                ])

                # Route-maps

                config_lines.extend([
                    "!\n",
                    "route-map FROM-CUSTOMER-IN permit 10\n",
                    f" set community {as_id}:100\n", # On marque la route comme client
                    " set local-preference 200\n", # On lui donne une priorité forte pour qu'elle soit préférée aux autres
                    "!\n",

                    "route-map FROM-PROVIDER-IN permit 10\n",
                    f" set community {as_id}:300\n", # On marque la route comme provider
                    " set local-preference 100\n", # On lui donne une priorité faible
                    "!\n",

                    "route-map TO-PROVIDER-OUT permit 10\n",
                    " match community CUSTOMER\n", # Si la route appartient à un de mes clients, alors je l'annonce à mon provider
                    "!\n", # Les autres routes ne lui seront pas annoncées

                    "route-map TAG-SELF permit 10\n",
                    f" set community {as_id}:100\n", # On utilise le tag customer
                    " set local-preference 200\n",   # Priorité maximale car c'est chez nous
                    "!\n"
                

                    # Pour les routeurs internes qui reçoivent des routes via iBGP 
                    # Gestion de la local pref interne basée sur les tags
                    "route-map SET-LOCAL-PREF permit 10\n",
                    " match community CUSTOMER\n",
                    " set local-preference 200\n",

                    "route-map SET-LOCAL-PREF permit 20\n",
                    " match community PEER\n",
                    " set local-preference 150\n",

                    "route-map SET-LOCAL-PREF permit 30\n",
                    " set local-preference 100\n"
                ])
            
            i += 1
            
        

        with open(path, "w") as f:
            f.writelines(config_lines)

if __name__ == "__main__":
    writeBGPconfig(routing_data)