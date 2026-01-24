 

import json

with open('intent.json', 'r') as file:
    routing_data = json.load(file)

def writeBGPconfig(data):

    # 1. Créer un dict pour trouver l'AS d'un routeur rapidement
    router_to_as = {}
    for as_id, as_info in data["AS"].items():
        for r in as_info["routers"]:
            router_to_as[r] = as_id

     # 2. Parcourir tous les routeurs 
    for r_name, as_id in router_to_as.items():
        r_info = data["AS"][as_id]["routers"][r_name]
        path = f"config/R{r_name[1:]}_i{r_name[1:]}_startup-config.cfg"

        with open(path, "r") as f:
            config = f.readlines()

        config_lines = []
        neighbors = []
        i = 0

        while i < len(config):
            
            # on réecrit ce qu'il y avait avant dans le fichier config
            config_lines.append(config[i])

            if (
                config[i] == "!\n"
                and config[i+1] == "!\n"
                and i + 2 < len(config)
                and config[i+2] == "ip forward-protocol nd\n"
            ):
                
                
                # ---- BGP
                config_lines.extend([
                    f"router bgp {as_id}\n",
                    f" bgp router-id {r_name[1:]}.{r_name[1:]}.{r_name[1:]}.{r_name[1:]}\n",
                    " bgp log-neighbor-changes\n",
                    " no bgp default ipv4-unicast\n"
                ])

                
                # On détecte les routeurs de bordure
                # ---- eBGP (interfaces)
                border_routers = []
                for int_info in r_info["interfaces"].values():
                    neighbor = int_info.get("ngbr")
                    neighbor_as = router_to_as.get(neighbor)
                    if neighbor_as and neighbor_as != as_id:
                        border_routers.append(neighbor_as)

                        as_type = data["AS"][as_id]["ngbr_AS"][neighbor_as]
                        remote_ip = None
                        for n_int in data["AS"][neighbor_as]["routers"][neighbor]["interfaces"].values():
                            if n_int.get("ngbr") == r_name:
                                remote_ip = n_int["ipv6"].split("/")[0]

                        if remote_ip:
                            neighbors.append({
                                "ip": remote_ip,
                                "type": as_type,
                                "remote_as": neighbor_as,
                                "ebgp": True
                            })

                        config_lines.extend([
                            f" neighbor {remote_ip} remote-as {neighbor_as}\n",
                            f" neighbor {remote_ip} description {as_type.upper()}-{neighbor}-AS{neighbor_as}\n",
                        ])
                

                # ---- iBGP (loopbacks)
                for other_r, other_info in data["AS"][as_id]["routers"].items():
                    if other_r != r_name:
                        if "Loopback0" in other_info["interfaces"]:
                            loop_ip = other_info["interfaces"]["Loopback0"]["ipv6"].split("/")[0]
                            neighbors.append({
                                "ip": loop_ip,
                                "ebgp": False
                            })
                            
                            config_lines.extend([
                                f" neighbor {loop_ip} remote-as {as_id}\n",
                                f" neighbor {loop_ip} update-source Loopback0\n",
                            ])


                
                # ---- address-family ipv6
                config_lines.extend(["!\n",
                    " address-family ipv6\n",
                ])
              

                # Utilisation d'un set pour éviter d'annoncer deux fois le même réseau
                # (par exemple si deux interfaces sont sur le même segment)
                networks = set()

                for int_info in r_info["interfaces"].values():
                    if "ipv6" in int_info:
                        prefix = ":".join(int_info["ipv6"].split(":")[:3]) + "::/64"
                        networks.add(prefix)

                # On écrit les commandes network dans la config
                for net in sorted(networks):
                    config_lines.append(f"  network {net}\n")


                for n in neighbors:
                    config_lines.append(f"  neighbor {n['ip']} activate\n")
                    config_lines.append(f"  neighbor {n['ip']} send-community\n")

                    if n.get("ebgp"):
                        # --- LOGIQUE eBGP (Bordure de l'AS) ---
                        
                        if n.get("type") == "customer":
                            # Si c'est MON client : je marque ses routes avec LocPrf 200
                            config_lines.append(f"  neighbor {n['ip']} route-map FROM-CUSTOMER-IN in\n")
                            # Je lui envoie tout (pas de route-map out restrictive)
                            
                        elif n.get("type") == "provider":
                            # Si c'est MON provider :
                            # 1. Je ne lui envoie QUE mes routes clients (sécurité)
                            config_lines.append(f"  neighbor {n['ip']} route-map TO-PROVIDER-OUT out\n")
                            # 2. Je baisse la priorité de ses routes à 100
                            config_lines.append(f"  neighbor {n['ip']} route-map FROM-PROVIDER-IN in\n")

                    else:
                        # --- LOGIQUE iBGP (Interne) ---
                        # Je lis les tags posés par mes routeurs de bordure
                        config_lines.append(f"  neighbor {n['ip']} route-map SET-LOCAL-PREF in\n")

                config_lines.append(" exit-address-family\n!\n")
                
                # communautés :
                config_lines.extend([
                    f"ip community-list standard CUSTOMER permit {as_id}:100\n",
                    f"ip community-list standard PEER permit {as_id}:200\n",
                    f"ip community-list standard PROVIDER permit {as_id}:300\n!\n"
                ])

                # ---------- Route-maps ----------

                # ---------- Génération des Route-maps ----------
                config_lines.extend([
                    "!\n",
                    "route-map FROM-CUSTOMER-IN permit 10\n",
                    f" set community {as_id}:100\n",
                    " set local-preference 200\n",
                    "!\n",
                    "route-map FROM-PROVIDER-IN permit 10\n",
                    f" set community {as_id}:300\n",
                    " set local-preference 100\n",
                    "!\n",
                    "route-map TO-PROVIDER-OUT permit 10\n",
                    " match community CUSTOMER\n", # On ne laisse passer que les clients
                    "!\n",
                    "route-map TO-PROVIDER-OUT permit 20\n",
                    "!\n",
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