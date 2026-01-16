import json
from pathlib import Path
from ospf_routing import Ospf_Routing
from rip_routing import rip_routing
from drag_and_drop import drag_and_drop


def load_intent(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def dump_intent(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

def set_prefix(data,source):
    autonomous_systems = data.get('AS', {})
    for autonomous_system, as_data in autonomous_systems.items():
        as_data['network']['prefix'] = f"2001:{autonomous_system}:"
        as_data['network']['subnet'] = '/64'
    dump_intent(source, data)

def set_address(data,source):
    autonomous_systems = data.get('AS', {})
    for as_id, as_data in autonomous_systems.items():
        prefix = as_data['network']['prefix']
        for router, router_data in as_data.get('routers', {}).items():
            r_id = router[1:] # Extrait le chiffre de "R1" -> "1"
            for interface, interface_data in router_data.get('interfaces', {}).items():
                
                # --- LOGIQUE LOOPBACK ---
                if interface == "Loopback0":
                    interface_data['ipv6'] = f"2001:DB8:{r_id}::1"
                    interface_data['mask'] = "/128"
                    continue
                
                # --- LOGIQUE INTERFACES PHYSIQUES ---
                neighbor = interface_data.get('ngbr')
                if neighbor and interface_data.get('ipv6') == '':
                    n_id = neighbor[1:]
                    interface_data['ipv6'] = f"{prefix}{r_id}{n_id}::{r_id}"
                    interface_data['mask'] = "/64"

    dump_intent(source, data)

def create_config_files(data):
    # Créer le dossier config s'il n'existe pas pour éviter le crash
    Path("config").mkdir(exist_ok=True)
    autonomous_systems = data.get('AS', {})
    for as_id, as_data in autonomous_systems.items():
        for router in as_data.get('routers', {}).keys():
            r_id = router[1:]
            open(f"config/{router}_i{r_id}_private-config.cfg", "w").close()
            open(f"config/{router}_i{r_id}_startup-config.cfg", "w").close()

def config_interfaces(data):
    autonomous_systems = data.get('AS', {})
    for as_id, as_data in autonomous_systems.items():
        for router, router_data in as_data.get('routers', {}).items():
            r_id = router[1:]
            with open(f"config/{router}_i{r_id}_startup-config.cfg", "w", encoding='utf-8') as file:
                # Header Standard
                file.write(f"!\nhostname R{r_id}\n!\nboot-start-marker\nboot-end-marker\n!\n")
                file.write("no aaa new-model\nip cef\nipv6 unicast-routing\nipv6 cef\n!\n")
                
                # Configuration des interfaces
                for interface, interface_data in router_data.get('interfaces', {}).items():
                    file.write(f"interface {interface}\n")
                    file.write(" no ip address\n")
                    
                    # On utilise le masque spécifique (/128 ou /64) défini dans set_address
                    mask = interface_data.get('mask', '/64')
                    ipv6 = interface_data.get('ipv6', '')
                    
                    if ipv6:
                        if interface != "Loopback0":
                            file.write(" ipv6 enable\n")
                            file.write(" negotiation auto\n")
                            file.write(" no shutdown\n")
                        file.write(f" ipv6 address {ipv6}{mask}\n")
                    file.write("!\n")

                # Footer Standard
                file.write("!\nip forward-protocol nd\n!\nno ip http server\nno ip http secure-server\n!\ncontrol-plane\n!\ncontrol-plane\n!\nline con 0\n exec-timeout 0 0\n privilege level 15\n logging synchronous\nline vty 0 4\n login\n!\nend\n")
        rip_routing(as_id,data)
        Ospf_Routing(as_id,data)
# Exécution
source = 'intent2.json'
data = load_intent(source)
set_prefix(data,source)
set_address(data,source)
dynamips = Path("gabin/project-files/dynamips")
create_config_files(data)
config_interfaces(data)
drag_and_drop(dynamips)
print("Configurations générées avec succès dans le dossier /config")