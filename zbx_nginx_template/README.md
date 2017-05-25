#zbx_nginx_template

Zabbix template for Nginx (python)

The template and the script are based on https://github.com/blacked/zbx_nginx_template

It's accumulate nginx stats and parse the log file (one at a time) and push result in Zabbix through trap-messages

##System requirements

- [python3](http://www.python.org/downloads/)
- [nginx](http://nginx.org/) with configured http_stub_status_module and access.log

## What's logging:

- Request\sec
- Response codes (200,301,302,403,404,500,503)\min
- HTTP Request methods avg request handling time (OPTIONS, GET, POST, HEAD, PUT, DELETE, TRACE, CONNECT)
- HTTP Request methods avg upstream response time
- Active\Keepalive connections
- Header and body reading
- Accepted, handled connections

## Install

1) Create a new regular expression named "Nginx log files for discovery". The expressions need to match the filename 
format you are using for your Nginx log files. For example, Expression type "Result is TRUE" and Expression `^.*access.log$`. This will match all files ending in "access.log".

2) Put the `userparameter_nginx.conf` file into the `/etc/zabbix/zabbix_agent.d` folder on your Zabbix agent hosts.

3) Put `zbx_nginx_stats.py` and `zbx_nginx_discovery.py` into your scripts path (like: `/etc/zabbix/script/nginx/`) on your Zabbix agent hosts.

2) Change the settings section in `zbx_nginx_stats.py`, to your configuration:

```
zabbix_host = '127.0.0.1'  # Zabbix server IP
zabbix_port = 10051  # Zabbix server port
hostname = 'Zabbix Agent'  # Name of monitored host, like it shows in zabbix web ui
time_delta = 1  # grep interval in minutes

# URL to nginx stat (http_stub_status_module)
stat_url = 'http://localhost/nginx_stat'

# Optional Basic Auth
username = 'user'
password = 'pass'
```

3) In the script path (`/etc/zabbix/script/nginx/`) do:
```bash
$ sudo chmod +x zbx_nginx_stats.py
$ sudo chmod +x zbx_nginx_discovery.py
```

4) Configure cron to run script every one minute with one entry for each log file being monitored:
```
$ sudo crontab -e

*/1 * * * * /etc/zabbix/script/nginx/zbx_nginx_stats.py <logfile>
```

5) Import the `zbx_nginx_template.xml` file into Zabbix in the Template section of the Web UI.

6) Add the following configurations to you Nginx configuration file:
```
location /nginx_stat {
  stub_status on;       # Turn on nginx stats
  access_log   off;     # We do not need logs for stats
  allow 127.0.0.1;      # Security: Only allow access from IP
  deny all;             # Deny requests from the other of the world
}
```

# Bonus

For an extra dose of awesomeness, make your Zabbix notify you on Telegram!
[Check this out](https://github.com/GabrielRF/Zabbix-Telegram-Notification)

