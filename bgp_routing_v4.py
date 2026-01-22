import json

with open("intent.json", "r") as file:
    routing_data = json.load(file)


def write_bgp_config(data):
    # 1. Dictionnaire routeur -> AS
    router_to_as = {}
    for as_id, as_info in data["AS"].items():
        for r in as_info["routers"]:
            router_to_as[r] = as_id

    # 2. Parcours de tous les routeurs
    for r_name, as_id in router_to_as.items():
        r_info = data["AS"][as_id]["routers"][r_name]
        path = f"config/R{r_name[1:]}_i{r_name[1:]}_startup-config.cfg"

        with open(path, "r") as f:
            config = f.readlines()

        config_lines = []
        neighbors = set()
        i = 0

        while i < len(config):
            # on réécrit ce qu'il y avait avant dans le fichier config
            config_lines.append(config[i])

            if (
                config[i] == "!\n"
                and config[i + 1] == "!\n"
                and i + 2 < len(config)
                and config[i + 2] == "ip forward-protocol nd\n"
            ):
                # ---- ROUTEURS DE BORDURE
                border_as_list = []
                for int_info in r_info["interfaces"].values():
                    neighbor = int_info.get("ngbr")
                    neighbor_as = router_to_as.get(neighbor)
                    if neighbor_as and neighbor_as != as_id:
                        if neighbor_as not in border_as_list:
                            border_as_list.append(neighbor_as)

                # ---- LISTES DE COMMUNAUTÉS
                config_lines.extend(
                    [
                        f"ip community-list standard CUSTOMER permit {as_id}:100\n",
                        f"ip community-list standard PEER permit {as_id}:200\n",
                        f"ip community-list standard PROVIDER permit {as_id}:300\n",
                        "!\n",
                    ]
                )

                # ---- ROUTE-MAPS D'ENTRÉE (tag communities)
                # FROM-CUSTOMER / FROM-PEER / FROM-PROVIDER / FROM-IBGP
                already_done_from = set()
                for border_as in border_as_list:
                    rel = data["AS"][as_id]["ngbr_AS"].get(border_as)
                    if rel == "customer" and "customer" not in already_done_from:
                        config_lines.extend(
                            [
                                "route-map FROM-CUSTOMER permit 10\n",
                                f" set community {as_id}:100 additive\n",
                                "!\n",
                            ]
                        )
                        already_done_from.add("customer")
                    if rel == "peer" and "peer" not in already_done_from:
                        config_lines.extend(
                            [
                                "route-map FROM-PEER permit 10\n",
                                f" set community {as_id}:200 additive\n",
                                "!\n",
                            ]
                        )
                        already_done_from.add("peer")
                    if rel == "provider" and "provider" not in already_done_from:
                        config_lines.extend(
                            [
                                "route-map FROM-PROVIDER permit 10\n",
                                f" set community {as_id}:300 additive\n",
                                "!\n",
                            ]
                        )
                        already_done_from.add("provider")

                config_lines.append("route-map FROM-IBGP permit 10\n!\n")

                # ---- LOCAL-PREF (SET-LOCAL-PREF)
                config_lines.extend(
                    [
                        "route-map SET-LOCAL-PREF permit 10\n",
                        " match community CUSTOMER\n",
                        " set local-preference 200\n",
                        "!\n",
                    ]
                )
                config_lines.extend(
                    [
                        "route-map SET-LOCAL-PREF permit 20\n",
                        " match community PEER\n",
                        " set local-preference 150\n",
                        "!\n",
                    ]
                )
                config_lines.extend(
                    [
                        "route-map SET-LOCAL-PREF permit 30\n",
                        " match community PROVIDER\n",
                        " set local-preference 100\n",
                        "!\n",
                    ]
                )

                # ---- ROUTE-MAPS D'EXPORT
                # Politique classique :
                # - TO-CUSTOMER : tout (pas de match, donc tout passe)
                # - TO-PEER : seulement ce qui vient de CUSTOMER
                # - TO-PROVIDER : seulement ce qui vient de CUSTOMER
                # - TO-IBGP : tout
                need_to_customer = False
                need_to_peer = False
                need_to_provider = False

                for border_as in border_as_list:
                    rel = data["AS"][as_id]["ngbr_AS"].get(border_as)
                    if rel == "customer":
                        need_to_customer = True
                    if rel == "peer":
                        need_to_peer = True
                    if rel == "provider":
                        need_to_provider = True

                if need_to_customer:
                    config_lines.append("route-map TO-CUSTOMER permit 10\n!\n")

                if need_to_peer:
                    config_lines.extend(
                        [
                            "route-map TO-PEER permit 10\n",
                            " match community CUSTOMER\n",
                            "!\n",
                        ]
                    )

                if need_to_provider:
                    config_lines.extend(
                        [
                            "route-map TO-PROVIDER permit 10\n",
                            " match community CUSTOMER\n",
                            "!\n",
                        ]
                    )

                config_lines.append("route-map TO-IBGP permit 10\n!\n")

                # ---- PROCESS BGP
                config_lines.extend(
                    [
                        f"router bgp {as_id}\n",
                        f" bgp router-id {r_name[1:]}.{r_name[1:]}.{r_name[1:]}.{r_name[1:]}\n",
                        " bgp log-neighbor-changes\n",
                        " no bgp default ipv4-unicast\n",
                        "!\n",
                    ]
                )

                # ---- eBGP (interfaces)
                for int_info in r_info["interfaces"].values():
                    neighbor = int_info.get("ngbr")
                    neighbor_as = router_to_as.get(neighbor)

                    if not neighbor_as or neighbor_as == as_id:
                        continue

                    as_type = data["AS"][as_id]["ngbr_AS"][neighbor_as]
                    remote_ip = None

                    for n_int in data["AS"][neighbor_as]["routers"][neighbor][
                        "interfaces"
                    ].values():
                        if n_int.get("ngbr") == r_name:
                            remote_ip = n_int["ipv6"].split("/")[0]

                    if remote_ip:
                        config_lines.extend(
                            [
                                f" neighbor {remote_ip} remote-as {neighbor_as}\n",
                                f" neighbor {remote_ip} description {as_type.upper()}-{neighbor}-AS{neighbor_as}\n",
                                " neighbor {0} send-community\n".format(remote_ip),
                                f" neighbor {remote_ip} route-map FROM-{as_type.upper()} in\n",
                                f" neighbor {remote_ip} route-map TO-{as_type.upper()} out\n",
                                "!\n",
                            ]
                        )
                        neighbors.add(remote_ip)

                # ---- iBGP (loopbacks)
                for other_r in data["AS"][as_id]["routers"]:
                    if other_r == r_name:
                        continue

                    remote_router = data["AS"][as_id]["routers"][other_r]
                    if "Loopback0" in remote_router["interfaces"]:
                        loop_ip = remote_router["interfaces"]["Loopback0"]["ipv6"].split(
                            "/"
                        )[0]
                        config_lines.extend(
                            [
                                f" neighbor {loop_ip} remote-as {as_id}\n",
                                f" neighbor {loop_ip} description iBGP-AS{as_id}\n",
                                " neighbor {loop} update-source Loopback0\n".format(
                                    loop=loop_ip
                                ),
                                f" neighbor {loop_ip} send-community\n",
                            ]
                        )
                        neighbors.add(loop_ip)

                # ---- address-family ipv6
                config_lines.extend(
                    [
                        "!\n",
                        " address-family ipv6\n",
                    ]
                )

                networks_to_advertise = set()

                for int_name, int_info in r_info["interfaces"].items():
                    full_ipv6 = int_info.get("ipv6")
                    if full_ipv6:
                        # ex: 2001:101:31::3/64 -> 2001:101:31::/64
                        ipv6_addr = full_ipv6.split("/")[0]
                        parts = ipv6_addr.split(":")
                        prefix_part = ":".join(parts[:3]) + "::/64"
                        networks_to_advertise.add(prefix_part)

                for net in sorted(networks_to_advertise):
                    config_lines.append(f" network {net}\n")

                config_lines.append("!\n")

                for n in neighbors:
                    config_lines.append(f" neighbor {n} activate\n")
                    if n.startswith("2001:DB8"):
                        config_lines.append(
                            " neighbor {0} route-map SET-LOCAL-PREF in\n".format(n)
                        )

                config_lines.append(" exit-address-family\n")

            i += 1

        with open(path, "w") as f:
            f.writelines(config_lines)


if __name__ == "__main__":
    write_bgp_config(routing_data)
