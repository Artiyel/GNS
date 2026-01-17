# à dégager dès que l'on pourra appeler la fonction depuis le main
import json
with open('intent2.json', 'r') as file:
    routing_data = json.load(file)

import configparser



def Ospf_Routing(AS_number, routing_data=routing_data):
    '''
    :param AS_number:
    :param routing_data: les informations contenues dans le fichier json
    '''
    if routing_data["AS"][AS_number]["igp"] == "OSPF":
        for router in routing_data["AS"][AS_number]["routers"]:
            Write_Ospf(router,AS_number)


def Write_Ospf(router,AS_number):
        '''
        :param router: Le routeur avec ses informations (dans le fichier intent.json)
        :param AS_number:
        '''
        process_id = router[1:]
        area_id = AS_number[1:]

        path = "config/R"+process_id+"_i"+process_id+"_startup-config.cfg"
        line = " ipv6 ospf " + process_id + " area " + area_id +"\n"

        waitinglist = []
        for interface in routing_data["AS"][AS_number]["routers"][router]["interfaces"]:
            waitinglist.append(interface)
            
        
        with open(path, "r") as f:
                config = f.readlines()

        newconfig = []
        i=0 #numero de la ligne
        n=0 #numero du routeur
        verif = 0 #on vérifie si on a bien tout écrit
        while i < len(config):
            #on détecte l'interface qui nous intéresse
            if n<len(waitinglist) and config[i] == "interface " + waitinglist[n] + "\n":
                while config[i]!="!\n":
                    newconfig.append(config[i])
                    i+=1
                #on ajoute la ligne de configuration
                newconfig.append(line)
                n+=1
                verif+=1
                if not config[i+1].startswith("interface"):
                    newconfig.append("!\n")
                    newconfig.append("router ospf "+process_id+"\n")
                    newconfig.append("!\n")

                    i+=1
                    n=0
            else : 
                newconfig.append(config[i])
                i+=1

            # Si on a été bloqué par l'absence d'une interface, on recommence sans
            if i == len(config)-1 and verif != len(waitinglist):
                print(f"Warning, interface {waitinglist[verif]} is missing for router R{process_id} !")
                i=0
                waitinglist.pop(verif)
                newconfig=[]
        j = 0
        NewNewConfig=[]
        while j < len(newconfig) : 
            NewNewConfig.append(newconfig[j])
            if newconfig[j].startswith("no ip http secure-server"):
                NewNewConfig.append("!\n")
                NewNewConfig.append("ipv6 router ospf "+process_id+"\n")
                NewNewConfig.append(f" router-id {process_id}.{process_id}.{process_id}.{process_id}\n")
                NewNewConfig.append(" redistribute bgp " + AS_number + "\n")
            j+=1

        #on ecrit la nouvelle config
        with open(path,"w") as f:
            for line in NewNewConfig:
                f.write(line)

if __name__ == "__main__":
    Ospf_Routing("102")