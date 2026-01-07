# à dégager dès que l'on pourra appeler la fonction depuis le main
import json
with open('test.json', 'r') as file:
    routing_data = json.load(file)

import configparser



def Ospf_Routing(AS_number, routing_data=routing_data):
    for router in routing_data["AS"][AS_number]["routers"]:
        process_id = router[1:]
        area_id = AS_number[1:]
        for interface in routing_data["AS"][AS_number]["routers"][router]["interfaces"]:
            Write_Ospf(interface,process_id,area_id)


def Write_Ospf(interface, process_id, area_id): 
    path = "Test/R"+process_id+"_configs_i"+process_id+"_startup-config.cfg"
    line = "ipv6 ospf " + process_id + " area " + area_id
    with open(path, "r") as f:
        config = f.readline()
        print(config)
    with open(path, "w") as f:
        for line in config:
            if line == "interface " + interface:

                print(file)


Ospf_Routing("101")