# à dégager dès que l'on pourra appeler la fonction depuis le main
import json
with open('intent.json', 'r') as file:
    routing_data = json.load(file)

import configparser



def Ospf_Routing(AS_number, routing_data=routing_data):
    if routing_data["AS"][AS_number]["igp"] == "OSPF":
        for router in routing_data["AS"][AS_number]["routers"]:
            Write_Ospf(router,AS_number)


def Write_Ospf(router,AS_number):
        process_id = router[1:]
        area_id = AS_number[1:]
        for interface in routing_data["AS"][AS_number]["routers"][router]["interfaces"]:

            path = "config/R"+process_id+"_i"+process_id+"_startup-config.cfg"
            line = " ipv6 ospf " + process_id + " area " + area_id +"\n"

            with open(path, "r") as f:
                config = f.readlines()

            newconfig = []
            i=0
            while i < len(config):
                #on détecte l'interface qui nous intéresse
                if config[i] == "interface " + interface + "\n":
                    while config[i]!="!\n":
                        newconfig.append(config[i])
                        i+=1
                        print(newconfig)
                    #on ajoute la ligne de configuration
                    newconfig.append(line)
                    if not config[i+1].startswith("interface"):
                        newconfig.append("!\n")
                        newconfig.append("router ospf "+process_id+"\n")
                        i+=1
                else : 
                    newconfig.append(config[i])
                    i+=1


            with open(path,"w") as f:
                for line in newconfig:
                    f.write(line)

Ospf_Routing("102")