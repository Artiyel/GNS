import json

with open('test.json', 'r') as file:
    routing_data = json.load(file)

def writeBGPconfig(data):

    # 1. Créer une map pour trouver l'AS d'un routeur rapidement
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
                and i + 2 < len(config)
                and config[i+1] == "!\n"
                and config[i+2] == "ip forward-protocol nd\n"
            ):
                # ---- BGP
                config_lines.extend([
                    f"router bgp {as_id}\n",
                    f" bgp router-id {r_name[1:]}.{r_name[1:]}.{r_name[1:]}.{r_name[1:]}\n",
                    " bgp log-neighbor-changes\n",
                    " no bgp default ipv4-unicast\n"
                ])

                # ---- iBGP (loopbacks)
                for other_r in data["AS"][as_id]["routers"]:
                    if other_r != r_name:
                        # On accède directement au routeur dans le bon AS
                        remote_router = data["AS"][as_id]["routers"][other_r]
        
                        # On vérifie si l'interface Loopback0 existe pour ce routeur
                        if "Loopback0" in remote_router["interfaces"]:
                            loop_ip = remote_router["interfaces"]["Loopback0"]["ipv6"].split("/")[0]
                            config_lines.append(
                                f" neighbor {loop_ip} remote-as {as_id}\n"
                            )
                            neighbors.add(loop_ip)

                # ---- eBGP (interfaces)
                for int_info in r_info["interfaces"].values():
                    neighbor = int_info.get("ngbr")
                    neighbor_as = router_to_as.get(neighbor)

                    if not neighbor_as or neighbor_as == as_id:
                        continue

                    remote_ip = None
                    for n_int in data["AS"][neighbor_as]["routers"][neighbor]["interfaces"].values():
                        if n_int.get("ngbr") == r_name:
                            remote_ip = n_int["ipv6"].split("/")[0]

                    if remote_ip:
                        config_lines.append(
                            f" neighbor {remote_ip} remote-as {neighbor_as}\n"
                        )
                        neighbors.add(remote_ip)

                # ---- address-family ipv6
                config_lines.extend([
                    " address-family ipv6\n",
                    "  redistribute connected\n"
                ])

                for n in neighbors:
                    config_lines.append(f"  neighbor {n} activate\n")

                config_lines.append(" exit-address-family\n")

            i += 1

        with open(path, "w") as f:
            f.writelines(config_lines)

writeBGPconfig(routing_data)