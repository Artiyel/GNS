import json

with open('test.json', 'r') as file:
    routing_data = json.load(file)



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

        path = "config/R"+r_name[1:]+"_i"+r_name[1:]+"_startup-config.cfg"

        config_lines=[]
        with open(path, "r") as f:
                config = f.readlines()

        i=0
        while i < len(config):
            config_lines.append(config[i])
            if config[i] == "!\n" and (i+2 < len(config)) and config[i+1] == "!\n" and config[i+2] == "ip forward-protocol nd\n" :
                # Début de la configuration BGP
                config_lines.append(
                    f"router bgp {as_id}",
                    f" bgp router-id {r_name[1:]}.{r_name[1:]}.{r_name[1:]}.{r_name[1:]}",
                    " bgp log-neighbor-changes",
                    " no bgp default ipv4-unicast"
                )

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
                            config_lines.append(f" neighbor {remote_ip} remote-as {neighbor_as}")
                   
                config_lines.append("address-family ipv6\n")
                config_lines.append(" redistribute connected\n")
                
        
                for nom_i, i_info in r_info["interfaces"].items():
                    if nom_i != "Loopback0" :
                        neighbor_name = i_info["ngbr"]
                        neighbor_as = router_to_as.get(neighbor_name)

                        for nom_int, n_int_info in data["AS"][neighbor_as]["routers"][neighbor_name]["interfaces"].items():
                            if nom_int == "Loopback0":
                                rem_ip = n_int_info["ipv6"]
                        if rem_ip :
                            config_lines.append(f" neighbor {rem_ip} activate")

                config_lines.append("exit-address-family\n")
                config_lines.append(config[i+1])
            i += 1

        # 4. Écriture du fichier .cfg
        with open(path, "w") as f: 
            f.write("\n".join(config_lines))


writeEBGPconfig(routing_data)