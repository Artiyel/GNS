 

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
        neighbors = set()
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
                # On détecte les routeurs de bordure
                border_routers = []
                for int_info in r_info["interfaces"].values():
                    neighbor = int_info.get("ngbr")
                    neighbor_as = router_to_as.get(neighbor)
                    if neighbor_as != as_id:
                        border_routers.append(neighbor_as)

                for int_info in r_info["interfaces"].values():
                    neighbor = int_info.get("ngbr")
                    neighbor_as = router_to_as.get(neighbor)
                    if not neighbor_as or neighbor_as == as_id:
                        continue
        
                    for n_int in data["AS"][neighbor_as]["routers"][neighbor]["interfaces"].values():
                        if n_int.get("ngbr") == r_name:

                            # ---- communautés BGP
                            config_lines.extend([
                                f"ip community-list standard CUSTOMER permit {as_id}:100\n",
                                f"ip community-list standard PEER permit {as_id}:200\n",
                                f"ip community-list standard PROVIDER permit {as_id}:300\n",
                                "!\n"
                            ])
                            
                            # ---- routes-maps BGP
                            for _as in border_routers:
                                value = data["AS"][as_id]["ngbr_AS"].get(_as)
                                if value == "customer" : 
                                    config_lines.extend([
                                        f"route-map FROM-CUSTOMER permit 10\n",
                                        f" set community {as_id}:100 additive\n",
                                        "!\n"
                                    ])
                                if value == "provider" : 
                                    config_lines.extend([
                                        f"route-map FROM-PROVIDER permit 10\n",
                                        f" set community {as_id}:300 additive\n",
                                        "!\n"
                                    ])
                                if value == "peer" : 
                                    config_lines.extend([
                                        f"route-map FROM-PEER permit 10\n",
                                        f" set community {as_id}:200 additive\n",
                                        "!\n"
                                    ])

                            config_lines.append(f"route-map FROM-IBGP permit 10\n!\n")
                            

                            # Local-pref 
                            config_lines.extend([
                                        f"route-map SET-LOCAL-PREF permit 10\n",
                                        f" match community CUSTOMER\n",
                                        f" set local-preference 200\n",
                                        "!\n"
                                    ])
                            
                            config_lines.extend([
                                        f"route-map SET-LOCAL-PREF permit 20\n",
                                        f" match community PEER\n",
                                        f" set local-preference 150\n",
                                        "!\n"
                                    ])
                            
                            config_lines.extend([
                                        f"route-map SET-LOCAL-PREF permit 30\n",
                                        f" match community PROVIDER\n",
                                        f" set local-preference 100\n",
                                        "!\n"
                                    ])
                            
                            # Export
                            for _as in border_routers:
                                value = data["AS"][as_id]["ngbr_AS"].get(_as)
                                if value == "customer":
                                    config_lines.append("route-map TO-CUSTOMER permit 10\n!\n")

                                if value == "peer":
                                    config_lines.append("route-map TO-PEER permit 10\n")
                                    config_lines.append(" match community CUSTOMER\n!\n")

                                if value == "provider":
                                    config_lines.append("route-map TO-PROVIDER permit 10\n")
                                    config_lines.append(" match community CUSTOMER\n!\n")
                            config_lines.append(f"route-map TO-IBGP permit 10\n!\n")


                 # ---- BGP
                config_lines.extend([
                    f"router bgp {as_id}\n",
                    f" bgp router-id {r_name[1:]}.{r_name[1:]}.{r_name[1:]}.{r_name[1:]}\n",
                    " bgp log-neighbor-changes\n",
                    " no bgp default ipv4-unicast\n!\n"
                ])

                # ---- eBGP (interfaces)
                for int_info in r_info["interfaces"].values():
                    neighbor = int_info.get("ngbr")
                    neighbor_as = router_to_as.get(neighbor)
                    print(neighbor_as, as_id)
                    

                    if not neighbor_as or neighbor_as == as_id:
                        continue 
                    
                    as_type = data["AS"][as_id]["ngbr_AS"][neighbor_as] 
            
                    remote_ip = None
                    for n_int in data["AS"][neighbor_as]["routers"][neighbor]["interfaces"].values():
                        if n_int.get("ngbr") == r_name:
                            remote_ip = n_int["ipv6"].split("/")[0]

                    if remote_ip:
                        config_lines.extend([
                            f" neighbor {remote_ip} remote-as {neighbor_as}\n",
                            f" neighbor {remote_ip} description {as_type.upper()}-{neighbor}-AS{neighbor_as}\n",
                            f" neighbor {remote_ip} send-community\n",
                            f" neighbor {remote_ip} route-map FROM-{as_type.upper()} in\n",
                            f" neighbor {remote_ip} route-map TO-{as_type.upper()} out\n",
                            "!\n"
                            
                        ])
                        neighbors.add(remote_ip)

                # ---- iBGP (loopbacks)
                for other_r in data["AS"][as_id]["routers"]:
                    if other_r != r_name:
                        # On accède directement au routeur dans le bon AS
                        remote_router = data["AS"][as_id]["routers"][other_r]
                    
                        # On vérifie si l'interface Loopback0 existe pour ce routeur
                        if "Loopback0" in remote_router["interfaces"]:
                            
                            loop_ip = remote_router["interfaces"]["Loopback0"]["ipv6"].split("/")[0]
                            config_lines.extend([
                                f" neighbor {loop_ip} remote-as {as_id}\n",
                                f" neighbor {loop_ip} description iBGP-AS{as_id}\n",
                                f" neighbor {loop_ip} update-source Loopback0\n",
                                f" neighbor {loop_ip} send-community\n"
                            ])
                            neighbors.add(loop_ip)

                
                
                # ---- address-family ipv6
                config_lines.extend(["!\n",
                    " address-family ipv6\n",
                ])
              

                # Utilisation d'un set pour éviter d'annoncer deux fois le même réseau
                # (par exemple si deux interfaces sont sur le même segment)
                networks_a_annoncer = set()

                for int_name, int_info in r_info["interfaces"].items():
                    full_ipv6 = int_info.get("ipv6")
                    if full_ipv6:
                        # On transforme l'IP en préfixe réseau /64
                        # ex: 2001:101:31::3/64 -> 2001:101:31::/64
                        prefix_part = ":".join(full_ipv6.split(":")[:3]) + "::/64"
                        networks_a_annoncer.add(prefix_part)

                # On écrit les commandes network dans la config
                for net in sorted(networks_a_annoncer):
                    config_lines.append(f"  network {net}\n")

                config_lines.append(f"!\n")

                for n in neighbors:
                    config_lines.append(f"  neighbor {n} activate\n")
                    if n.startswith("2001:DB8"):
                        config_lines.append(f"  neighbor {n} route-map SET-LOCAL-PREF in\n")

                config_lines.append(" exit-address-family\n")
                

            i += 1
        

        with open(path, "w") as f:
            f.writelines(config_lines)

if __name__ == "__main__":
    writeBGPconfig(routing_data)