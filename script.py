import json



def load_intent(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    return data

def dump_intent(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

data = load_intent('test.json')

def set_prefix(data):
    autonomous_systems = data.get('AS', {})
    for autonomous_system, as_data in autonomous_systems.items():
        as_data['network']['prefix'] = f"2001:{autonomous_system}:"
        as_data['network']['subnet'] = '/64'
    
    dump_intent('test.json', data)


def set_address(data):
    autonomous_systems = data.get('AS')
    
    for autonomous_system, as_data in autonomous_systems.items():
        for router, router_data in as_data.get('routers', {}).items():
            for interface, interface_data in router_data.get('interfaces', {}).items():
                neighbor = interface_data.get('ngbr')
                if interface_data.get('ipv6') == '':
                    interface_data['ipv6'] = f"{as_data['network']['prefix']}{router[1:]}{neighbor[1:]}::{router[1:]}"

                    
                    for ngbr_interface, ngbr_interface_data in as_data['routers'].get(neighbor, {}).items():
                        if ngbr_interface_data.get('ngbr') == router:
                            ngbr_interface_data['ipv6'] = f"{as_data['network']['prefix']}:{router}{neighbor[1:]}::{router[1:]}"



    dump_intent('test.json', data)

def create_config_files(data):
    autonomous_systems = data.get('AS')
    for autonomous_system, as_data in autonomous_systems.items():
        for router, router_data in as_data.get('routers', {}).items():
            open(f"config/{router}_i{router[1:]}_private-config.cfg", "w").close()
            open(f"config/{router}_i{router[1:]}_startup-config.cfg", "w").close()

def config_interfaces(data):
    autonomous_systems = data.get('AS')
    for autonomous_system, as_data in autonomous_systems.items():
        for router, router_data in as_data.get('routers', {}).items():
            with open(f"config/{router}_i{router[1:]}_startup-config.cfg", "a", encoding='utf-8') as file:
                file.write("!\n")
                file.write(f"hostname R{router[1:]}\n")
                file.write("!\n")

                file.write("boot-start-marker\n")
                file.write("boot-end-marker\n")
                file.write("!\n")
                
                file.write("no aaa new-model\n")
                file.write("no ip icmp rate-limit unreachable\n")
                file.write("ip cef\n")
                file.write("!\n")

                file.write("no ip domain lookup\n")
                file.write("ipv6 unicast-routing\n")
                file.write("ipv6 cef\n")
                file.write("!\n")

                file.write("multilink bundle-name authenticated\n")
                file.write("!\n")

                file.write("ip tcp synwait-time 5\n")
                file.write("!\n")

                file.write("interface Loopback0\n")
                file.write(" no ip address\n")
                file.write(f" ipv6 address 2001:DB8:{router[1:]}::1/128\n")
                if as_data['igp'] == 'RIP':
                    file.write(f" ipv6 rip p{router[1:]} enable\n")
                else:
                    file.write(f" ipv6 ospf {router[1:]} area 0\n")
                file.write("!\n")

                file.write("interface Ethernet0/0\n")
                file.write(" no ip address\n")
                file.write(" shutdown\n")
                file.write(" duplex auto\n")
                file.write("!\n")
                for interface, interface_data in router_data.get('interfaces', {}).items():                   

                    file.write(f"interface {interface}\n")
                    file.write(" no ip address\n")
                    file.write(" ipv6 enable\n")
                    file.write(f" ipv6 address {interface_data['ipv6']}{as_data['network']['subnet']}\n")
                    file.write(" no shutdown\n")
                    file.write("!\n")
                file.write("!\n")

set_prefix(data)
set_address(data)
create_config_files(data)
config_interfaces(data)