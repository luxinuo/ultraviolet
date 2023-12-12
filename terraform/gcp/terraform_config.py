#!/usr/bin/env python3
# -*- coding: utf-8 -*- #
__author__ = 'Lucas Lee'


import subprocess


input_cred_path = input("Please type your gcp credential path: ")
input_machine_type = input("Please type your gcp machine type(default e2-standard-2): ")
input_machine_type = input_machine_type if input_machine_type else 'e2-standard-2'

subprocess.run(f'cat {input_cred_path} > credentials.json', shell=True)
p1 = subprocess.run(f'cat {input_cred_path} | jq ".project_id"', shell=True, capture_output=True)
project_id = p1.stdout.decode('utf-8').replace('"', '').replace('\n', '')
print(project_id)



cmd = f'sed -e "s/GCP_PROJECT_ID/{project_id}/g" -e "s/GCP_MACHINE_TYPE/{input_machine_type}/g" main_template.tf > main.tf'
subprocess.run(cmd, shell=True)
