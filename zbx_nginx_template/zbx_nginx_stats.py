#!/usr/bin/python3

import urllib.request, urllib.parse, urllib.error, base64, re, struct, time, socket, datetime, os.path, argparse

try:
    import json
except:
    import simplejson as json

#####################################################################
#
# SETTINGS SECTION
#
#####################################################################

zabbix_host = '127.0.0.1'  # Zabbix server IP
zabbix_port = 10051  # Zabbix server port
hostname = 'Zabbix Agent'  # Name of monitored host, like it is shown on Zabbix WebUI
time_delta = 1  # grep interval in minutes

# URL to Nginx stat (http_stub_status_module)
stat_url = 'http://localhost/nginx_stat'

# Optional Basic Auth
username = 'user'
password = 'pass'

#####################################################################
#
# DO NOT CHANGE BEYOND THIS POINT
#
#####################################################################

parser = argparse.ArgumentParser()
parser.add_argument("logfile")
args = parser.parse_args()

nginx_log_file_path = args.logfile
filename = os.path.basename(nginx_log_file_path)

# Temp file, with log file cursor position
seek_file = '/tmp/seek_'+filename

class Metric(object):
    def __init__(self, host, key, value, clock=None):
        self.host = host
        self.key = key
        self.value = value
        self.clock = clock

    def __repr__(self):
        if self.clock is None:
            return 'Metric(%r, %r, %r)' % (self.host, self.key, self.value)
        return 'Metric(%r, %r, %r, %r)' % (self.host, self.key, self.value, self.clock)


def send_to_zabbix(metrics, zabbix_host='127.0.0.1', zabbix_port=10051):
    metrics_data = []
    for m in metrics:
        clock = m.clock or ('%d' % time.time())
        data = {
            "host": m.host,
            "key": m.key,
            "value": m.value,
            "clock": clock
        }
        metrics_data.append(data)

    data_json = {
        "request": "sender data",
        "data": metrics_data
    }
    HEADER = "ZBXD\1"
    data_json_str = json.dumps(data_json)
    data_len = len(data_json_str)
    data_header = struct.pack('<Q', data_len)
    packet = HEADER.encode() + data_header + data_json_str.encode()

    try:
        zabbix = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        zabbix.connect((zabbix_host, zabbix_port))
        zabbix.send(packet)
    except Exception as err:
        print("Error connecting to Zabbix server -- {0}".format(err))
        return False
    else:
        resp_hdr = zabbix.recv(5).decode()
        if not resp_hdr == 'ZBXD\1':
            print('Wrong zabbix response: %s' % resp_hdr)
            return False
        resp_data_header = zabbix.recv(8)
        resp_body_len = struct.unpack('<Q', resp_data_header)[0]
        resp_body = zabbix.recv(resp_body_len)
        zabbix.close()

        resp = json.loads(resp_body.decode())
        # print resp
        if resp.get('response') != 'success':
            print(('Got error from Zabbix: %s') % resp)
            return False
        return True


def get(url, login, passwd):
    req = urllib.request.Request(url)
    if login and passwd:
        base64string = base64.b64encode(('%s:%s' % (username, password)).encode()).decode().replace('\n', '')
        req.add_header("Authorization", "Basic %s" % base64string)
    q = urllib.request.urlopen(req)
    res = q.read()
    q.close()
    return res


def parse_nginx_stat(data):
    a = {}
    # Active connections
    a['active_connections'] = re.match(r'(.*):\s(\d*)', data[0], re.M | re.I).group(2)
    # Accepts
    a['accepted_connections'] = re.match(r'\s(\d*)\s(\d*)\s(\d*)', data[2], re.M | re.I).group(1)
    # Handled
    a['handled_connections'] = re.match(r'\s(\d*)\s(\d*)\s(\d*)', data[2], re.M | re.I).group(2)
    # Requests
    a['handled_requests'] = re.match(r'\s(\d*)\s(\d*)\s(\d*)', data[2], re.M | re.I).group(3)
    # Reading
    a['header_reading'] = re.match(r'(.*):\s(\d*)(.*):\s(\d*)(.*):\s(\d*)', data[3], re.M | re.I).group(2)
    # Writing
    a['body_reading'] = re.match(r'(.*):\s(\d*)(.*):\s(\d*)(.*):\s(\d*)', data[3], re.M | re.I).group(4)
    # Waiting
    a['keepalive_connections'] = re.match(r'(.*):\s(\d*)(.*):\s(\d*)(.*):\s(\d*)', data[3], re.M | re.I).group(6)
    return a


def read_seek(file):
    if os.path.isfile(file):
        f = open(file, 'r')
        try:
            result = int(f.readline())
            f.close()
            return result
        except:
            return 0
    else:
        return 0


def write_seek(file, value):
    f = open(file, 'w')
    f.write(value)
    f.close()


# print '[12/Mar/2014:03:21:13 +0400]'

d = datetime.datetime.now() - datetime.timedelta(minutes=time_delta)
minute = int(time.mktime(d.timetuple()) / 60) * 60
d = d.strftime('%d/%b/%Y:%H:%M')

total_rps = 0
rps = [0] * 60

res_code = {
    200: 0,
    300: 0,
    301: 0,
    302: 0,
    304: 0,
    307: 0,
    400: 0,
    401: 0,
    403: 0,
    404: 0,
    410: 0,
    500: 0,
    501: 0,
    503: 0,
    550: 0,
}

req_time = {
    'OTHER': [],
    'GET': [],
    'POST': [],
}

res_time = {
    'OTHER': [],
    'GET': [],
    'POST': [],
}

nf = open(nginx_log_file_path, 'r')

new_seek = seek = read_seek(seek_file)

# if new log file, don't do seek
if os.path.getsize(nginx_log_file_path) > seek:
    nf.seek(seek)

line = nf.readline()
while line:
    if d in line:
        new_seek = nf.tell()
        total_rps += 1
        match = re.match(r'.*:(\d+)\s.*"(\w+)\s.*"\s(\d*)\s.*(\d+\.\d+)\s(\d+\.\d+)\s\.', line)
        sec = int(match.group(1))
        req = match.group(2)
        code = match.group(3)
        req_time[req].append(float(match.group(4))) if req in req_time else req_time['OTHER'].append(
            float(match.group(4)))
        res_time[req].append(float(match.group(5))) if req in res_time else res_time['OTHER'].append(
            float(match.group(4)))
        if code in res_code:
            res_code[code] += 1
        else:
            res_code[code] = 1

        rps[sec] += 1
    line = nf.readline()

if total_rps != 0:
    write_seek(seek_file, str(new_seek))

nf.close()

data_to_send = []

# Adding the metrics to response
data = get(stat_url, username, password).decode().split('\n')
data = parse_nginx_stat(data)

for i in data:
    data_to_send.append(Metric(hostname, ('nginx.%s[%s]' % (i, filename)), data[i]))

# Adding the request per seconds to response
for t in range(0, 60):
    data_to_send.append(Metric(hostname, ('nginx.rps[%s]' % filename), rps[t], minute + t))

# Adding the response codes stats to response
for t in res_code:
    data_to_send.append(Metric(hostname, ('nginx.responses[%s,%s]' % (filename, t)), res_code[t]))

# Calculating the average request handling times and adding to response
req_time = {x: sum(req_time[x]) / float(len(req_time[x])) for x in req_time if len(req_time[x]) > 0}
for t in req_time:
    data_to_send.append(Metric(hostname, ('nginx.avg_req[%s,%s]' % (filename, t)), req_time[t]))

# Calculating the average upstream response times and adding to response
res_time = {x: sum(res_time[x]) / float(len(res_time[x])) for x in res_time if len(res_time[x]) > 0}
for t in res_time:
    data_to_send.append(Metric(hostname, ('nginx.avg_res[%s,%s]' % (filename, t)), res_time[t]))

send_to_zabbix(data_to_send, zabbix_host, zabbix_port)
