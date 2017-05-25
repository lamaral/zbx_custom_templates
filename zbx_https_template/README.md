# Zabbix template to check for HTTPS certs expiration

This template was meant to be used together with letsencrypt for HTTPS certificates expiration check. 

The discovery works only with the letsencrypt file structure.

## Installing the dependencies
'''bash
# apt-get install python3 python3-pip python3-dev
# pip3 install pyopenssl
#
'''

## Installing the check and discovery scripts
Create the `/usr/share/zabbix-agent/` dir and move all the .py into it.

## Configure Zabbix agent on the monitored machine
Copy the file https_cert_check.conf into `/etc/zabbix/zabbix_agentd.d` and restart Zabbix agent

## Import the template into zabbix
Import the zbx_https_cert_check.xml template file into Zabbix and assign it to the hosts to be monitored