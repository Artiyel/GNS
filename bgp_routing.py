import json

with open('test.json', 'r') as file:
    routing_data = json.load(file)

def find_border_routers(data):
    # 1. On crée d'abord un dictionnaire de correspondance {Nom_Router: AS_ID}
    # Cela permet de savoir instantanément à quel AS appartient n'importe quel routeur
    router_as_map = {}
    for as_id, as_info in data["AS"].items():
        for r_name in as_info["routers"]:
            router_as_map[r_name] = as_id

    border_routers = []

    # 2. On analyse chaque routeur pour vérifier ses voisins
    for as_id, as_info in data["AS"].items():
        for r_name, r_info in as_info["routers"].items():
            
            # On vérifie chaque interface du routeur actuel
            for int_info in r_info["interfaces"].values():
                neighbor_name = int_info["ngbr"]
                
                # Si le voisin appartient à un AS différent, c'est un routeur de bordure
                if neighbor_name in router_as_map:
                    if router_as_map[neighbor_name] != as_id:
                        if r_name not in border_routers:
                            border_routers.append(r_name)
                        break # Pas besoin de vérifier les autres interfaces de ce routeur
    
    return border_routers

def writeEBGPconfig(data):
    # 1. Créer une map pour trouver l'AS d'un routeur rapidement
    router_to_as = {}
    for as_id, as_info in data["AS"].items():
        for r_name in as_info["routers"]:
            router_to_as[r_name] = as_id

    # 2. Parcourir tous les routeurs 
    for r_name, as_id in router_to_as.items():
        as_id = router_to_as[r_name]
        r_info = data["AS"][as_id]["routers"][r_name]
        # Début de la configuration BGP
        config_lines = [
            f"router bgp {as_id}",
            f" bgp router-id {r_name[1:]}.{r_name[1:]}.{r_name[1:]}.{r_name[1:]}",
            " bgp log-neighbor-changes",
            " no bgp default ipv4-unicast"
        ]

        # 3. Identifier les interfaces BGP pour ce routeur
        for int_info in r_info["interfaces"].values():
            neighbor_name = int_info["ngbr"]
            neighbor_as = router_to_as.get(neighbor_name)

            # Si le voisin est dans un AS différent, c'est une session eBGP
            if neighbor_as and neighbor_as != as_id:
                # Trouver l'IP de l'interface du voisin qui nous fait face
                neighbor_interfaces = data["AS"][neighbor_as]["routers"][neighbor_name]["interfaces"]
                remote_ip = None
                for n_int_info in neighbor_interfaces.values():
                    if n_int_info["ngbr"] == r_name:
                        remote_ip = n_int_info["ipv6"]

                if remote_ip:
                    config_lines.append(f"  neighbor {remote_ip} remote-as {neighbor_as}")
            else :
                # Trouver l'IP de l'interface du voisin qui nous fait face
                neighbor_interfaces = data["AS"][neighbor_as]["routers"][neighbor_name]["interfaces"]
                remote_ip = None
                for n_int_info in neighbor_interfaces.values():
                    if n_int_info["ngbr"] == r_name:
                        remote_ip = n_int_info["ipv6"]

                if remote_ip:
                    config_lines.append(f"neighbor {remote_ip} remote-as {neighbor_as}")


        path = "config/R"+r_name[1:]+"_i"+r_name[1:]+"_startup-config.cfg"
        # 4. Écriture du fichier .cfg
        with open(path, "w") as f: 
            f.write("\n".join(config_lines))


liste = find_border_routers(routing_data)

writeEBGPconfig(routing_data)