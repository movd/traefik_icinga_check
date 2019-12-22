#!/usr/bin/env python3

import requests
from dotenv import load_dotenv
import os
import sys
import datetime
import re

load_dotenv()

# Get secret stuff from env file
TRAEFIK_API_HOSTNAME = os.getenv('TRAEFIK_API_HOSTNAME')
TRAEFIK_USERNAME = os.getenv('TRAEFIK_USERNAME')
TRAEFIK_PASSWORD = os.getenv('TRAEFIK_PASSWORD')

# List all routers from traefik
url = (f'http://{TRAEFIK_API_HOSTNAME}/api/http/routers')

try:
    response = requests.get(url, auth=(
            TRAEFIK_USERNAME, TRAEFIK_PASSWORD))
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    print(e)
    sys.exit(1)

# Convert API response from JSON to Python
routers = response.json()


# API Call for Endpoint matching
def get_is_ssl(entry_point):
    entry_point_api_url = (
        f'http://{TRAEFIK_API_HOSTNAME}/api/entrypoints/{entry_point}')
    try:
        response = requests.get(entry_point_api_url, auth=(
            TRAEFIK_USERNAME, TRAEFIK_PASSWORD))
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(e)
        sys.exit(1)

    entry_point = response.json()
    if '80' in entry_point['address']:
        return False
    if '443' in entry_point['address']:
        return True


def print_icinga(routers):
    # Loop trough all routers
    for router in routers:
        # Check if provider is docker
        if router['provider'] == 'docker':
            service = router['service']
            rules_str = router.get('rule', '')
            hostnames = re.sub(r'(Host\(\`)|(\`\))', '', rules_str).replace(
                ' ', '').replace('(', '').replace(')', '').split('||')
            entry_points = router.get('entryPoints', 'no entryPoints')
            for hostname in hostnames:
                # Check if entryPoint is ssl encrypted
                is_ssl = get_is_ssl(entry_points[0])
                ssl_checks = ''
                protocol = 'http'
                if is_ssl:
                    ssl_checks = f'''
                vars.http_ssl = "1"
                vars.http_sni = "true"
                    '''
                    protocol = 'https'

                service_name = (f'{hostname} {protocol} {service}')

                # Create services.conf for icinga2

                print(f'''apply Service "{service_name}" {{
                import "generic-service"
                check_command = "http"
                vars.http_address = "{hostname}"
                vars.http_vhost = "{hostname}"
                {ssl_checks}
                vars.notification["mail"] = {{
                    groups = [ "icingaadmins" ]
                }}

                notes = "Service: {service} Exposed at: \
<{protocol}://{hostname}/> \
Created by  {os.path.realpath(__file__)} \
at {datetime.datetime.now()}"
                assign where (host.address || host.address6) && \
host.vars.os == "Linux" && host.name != NodeName \
&& "docker" in host.vars.services
                }}
                ''')


print_icinga(routers)
