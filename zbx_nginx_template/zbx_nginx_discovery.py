#!/usr/bin/python3

import argparse
from os import listdir
from os.path import isfile, join
from json import dumps

parser = argparse.ArgumentParser()
parser.add_argument("logfolder")
args = parser.parse_args()

onlyfiles = [f for f in listdir(args.logfolder) if isfile(join(args.logfolder, f))]

jobs_in_dict = {
    "data": []
}
for x in onlyfiles:
    macro = {
        "{#LOGFILE}": x
    }
    jobs_in_dict["data"].append(macro)

jobs_in_json = dumps(jobs_in_dict)

print(jobs_in_json)
