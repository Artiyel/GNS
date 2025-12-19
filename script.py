import json
import re

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
        as_data['network']['prefix'] = f"2001:{autonomous_system}::"
        as_data['network']['subnet'] = '/64'
    
    dump_intent('test.json', data)


def set_address(data):
    autonomous_systems = data.get('AS')
    a = 1
    for autonomous_system, as_data in autonomous_systems.items():
        for router, router_data in as_data.get('routers', {}).items():
            router_data['address'] = f"{as_data['network']['prefix']}{a}"
        a += 1

    dump_intent('test.json', data)


set_prefix(data)