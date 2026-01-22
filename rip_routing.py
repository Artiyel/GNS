import json
with open('intent.json', 'r') as file:
    routing_data = json.load(file)

def rip_routing(AS_number, routing_data=routing_data):
    if routing_data["AS"][AS_number]["igp"] == "RIP":
        for router in routing_data["AS"][AS_number]["routers"]:
            write_rip(router,AS_number)
            
def write_rip(router, AS_number): 


    process_id = router[1:]
    area_id = AS_number[1:]
    path = "config/R"+process_id+"_i"+process_id+"_startup-config.cfg"
    line = f" ipv6 rip p{process_id} enable\n"
   
    with open(path, "r") as f:
        config = f.readlines()
        
        waitinglist = []
        for interface in routing_data["AS"][AS_number]["routers"][router]["interfaces"]:
            waitinglist.append(interface)

        newconfig = []
        i=0 #numero de la ligne
        n=0 #numero du routeur
        while i < len(config):
            #on détecte l'interface qui nous intéresse
            if n<len(waitinglist) and config[i] == "interface " + waitinglist[n] + "\n":
                while config[i]!="!\n":
                    newconfig.append(config[i])
                    i+=1
                #on ajoute la ligne de configuration
                if config[i-1].startswith(f" ipv6 address 2001:{AS_number}") or config[i-1].startswith(f" ipv6 address 2001:DB8") : 
                    newconfig.append(line)
                n+=1
                if not config[i+1].startswith("interface"):
                        newconfig.append("!\n")
                        newconfig.append("ipv6 router rip p"+process_id+"\n")
                        newconfig.append(" redistribute connected\n")
                        newconfig.append(" redistribute bgp " + AS_number + "\n")
                        newconfig.append("!\n")
                        i+=1
            else : 
                newconfig.append(config[i])
                i+=1

            # Si on a été bloqué par l'absence d'une interface, on recommence sans
            if i == len(config)-1 and n != len(waitinglist):
                print(f"Warning, interface {waitinglist[n]} is missing for router R{process_id} !")
                i=0
                waitinglist.pop(n)
                newconfig=[]

        #on ecrit la nouvelle config
        with open(path,"w") as f:
            for line in newconfig:
                f.write(line)         

if __name__ == "__main__":
    rip_routing("101")