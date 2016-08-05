#!/usr/bin/env python3
import json
import click
import base64
import pandas
import requests

def download_price_data():
  with  open ("price_index.csv", "wb") as price_index:
    data_stream = requests.get('https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/index.csv', stream=True)
    with click.progressbar(length=int(data_stream.headers['Content-Length']), label='Downloading Price Index::') as bar:
      for data in data_stream.iter_content(chunk_size = 1024 * 1024):
        price_index.write(data)
        bar.update(1024 * 1024)
  price_index.close()

def calculate_percentage_price(instance_type, region='us-west-2', percentage=30):
  region_map = {
               'us-east-1': 'US East (N. Virginia)',
               'us-west-1': 'US West (N. California)',
               'us-west-2': 'US West (Oregon)',
               'eu-west-1': 'EU (Ireland)',
               'eu-central-1': 'EU (Frankfurt)',
               'ap-northeast-1': 'Asia Pacific (Tokyo)',
               'ap-northeast-2': 'Asia Pacific (Seoul)',
               'ap-southeast-1': 'Asia Pacific (Singapore)',
               'ap-southeast-2': 'Asia Pacific (Sydney)',
               'ap-south-1': 'Asia Pacific (Mumbai)',
               'sa-east-1': 'South America (Sao Paulo)',
               }
  data = pandas.read_csv("price_index.csv",
                          sep = ',',
                          skiprows=5,
                          usecols=['TermType', 'PricePerUnit', 'Product Family', 'Location', 'Instance Type', 'Tenancy', 'Operating System'])

  filtered = data[(data.Location == region_map[region]) & 
                  (data['Instance Type'] == instance_type) &
                  (data['Product Family'] == 'Compute Instance') &
                  (data['Operating System'] == 'Linux') &
                  (data['Tenancy'] == 'Shared') &
                  (data['TermType'] == 'OnDemand')]
  return filtered.PricePerUnit.values[0] * percentage / 100

@click.command()
@click.option('--layer-id', required=True, help='Layer ID to add the Spot Fleet instances to.')
@click.option('--region', required=True, default='us-west-2', help='Region Name to create the Spot Fleet')
@click.option('--ami-id', required=True, default='ami-962fedf6', help='AMI to launch. Default is Ubuntu 14.04 LTS')
@click.option('--ssh-key', required=True, help='SSH Key for the instances')
@click.option('--subnet-ids', multiple=True, help='Subnets to launch the AMI -- Specify multipe times')
@click.option('--instance-types', required=True, multiple=True, default='c3.large', help='Instance Types to launch - Specify multiple times')
@click.option('--iam-fleet-role', required=True, help='IAM SpotFleet Rolei ARN')
@click.option('--iam-instance-profile', required=True, help='EC2 IAM Instance Profile ARN')
@click.option('--security-group-ids', required=True, multiple=True, help='Security Groups for the instances -- Specify mutiple times')
@click.option('--spot-price', required=True, type=int, help='Maximum Spot Price in % of on-Demand')
def generate_config_json(layer_id, region, ami_id, ssh_key, subnet_ids, instance_types, iam_fleet_role, iam_instance_profile, security_group_ids, spot_price):
  #AWS Client
  #Variables
  json_data = {}
  with open ("userdata.template", "r") as userdata:
    user_data=base64.b64encode(str(userdata.read()%{"layerid":layer_id}).encode('ascii'))
    userdata.close()
  #JSON Data	
  json_data['IamFleetRole'] = iam_fleet_role
  json_data["AllocationStrategy"] = "lowestPrice"
  json_data["TargetCapacity"] = 1
  json_data["SpotPrice"] = spot_price
  json_data["TerminateInstancesWithExpiration"] = True
  json_data["Type"] = "maintain"
  json_data["LaunchSpecifications"] = []
  for subnet_id in subnet_ids: 
    for instance_type in instance_types:
      launch_specifications = {}
      launch_specifications["ImageId"] = ami_id
      launch_specifications["InstanceType"] = instance_type
      launch_specifications["KeyName"] = ssh_key
      launch_specifications["SpotPrice"] = calculate_percentage_price(instance_type, region=region, percentage=spot_price)
      launch_specifications["IamInstanceProfile"] =  {}
      launch_specifications["IamInstanceProfile"]["Arn"] = iam_instance_profile
      launch_specifications["UserData"] = user_data.decode('ascii')
      launch_specifications["NetworkInterfaces"] = []
      
      network_interfaces = {}
      network_interfaces["DeviceIndex"] = 0
      network_interfaces["SubnetId"] = subnet_id
      network_interfaces["DeleteOnTermination"] = True
      network_interfaces["AssociatePublicIpAddress"] = True
      network_interfaces["Groups"] = security_group_ids
      launch_specifications["NetworkInterfaces"].append(network_interfaces)
      json_data["LaunchSpecifications"].append(launch_specifications)
  with  open ("config.json", "w") as config_json:
    config_json.write(json.dumps(json_data, indent=2))
    config_json.close()
    
download_price_data()
generate_config_json()
