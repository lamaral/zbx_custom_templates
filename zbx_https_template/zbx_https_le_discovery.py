#!/usr/bin/env python3
# Author: Luiz Amaral - https://www.luiz.eng.br/

import argparse
import json
from os import walk

def main():
    # Argument parsing
    parser = argparse.ArgumentParser()
    parser.add_argument('path', help='specify an host to connect to', type=str, default='/etc/letsencrypt/live/')
    args = parser.parse_args()

    # Zabbix wants the data in this format
    output = {
        "data": []
    }

    # This object will hold all the domains that need to be checked
    domains = []

    # Jerry-rig to get the directories inside letsencrypt dir
    for (dirpath, dirnames, filenames) in walk("/etc/letsencrypt/live/"):
        domains.extend(dirnames)
        break

    # Parse all the domain names and append them to the output data
    for domain in domains:
        macro = {
            "{#SNI}": domain
        }
        output["data"].append(macro)

    output_json = json.dumps(output)

    # Print the output json
    print(output_json)

if __name__ == "__main__":
    main()