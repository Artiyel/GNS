import json
with open('test.json', 'r') as file:
    routing_data = json.load(file)

def rip_routing(AS_number, routing_data=routing_data):
    for router in routing_data["AS"][AS_number]["routers"]:
        router_data = routing_data["AS"][AS_number]["routers"][router]
        process_id = router[1:]
        area_id = AS_number[1:]
        write_rip(router_data,process_id,area_id)
        
            
def write_rip(router_data, process_id, area_id): 
    path = "config/R"+process_id+"_i"+process_id+"_startup-config.cfg"
   
    with open(path, "r") as f:
        config = f.readlines()
        print(config)
        for interface in router_data["interfaces"]:
            for line in config:
                if line == "interface " + interface + "\n":
                    config.insert(config.index(line)+1, " ipv6 rip p" + process_id + " enable\n")
    
    with open(path, "w") as f:
        
        f.writelines(config)            
        f.write("ipv6 router rip p1\n")
        f.write(" redistribute connected\n")

rip_routing("101")