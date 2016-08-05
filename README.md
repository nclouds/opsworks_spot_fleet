#Spot Fleet Register and De-Register from Opsworks

##Requirements
1. A `EC2 Spot Fleet Role` to launch the spot fleet on your behalf.
2. An IAM Role to use as EC2 Instance Profile -- This role should have opsworks `register`, `deregister` and `assign` access
3. Opsworks Stack and a Layer for the instances to register to.

#Usage
1. Clone the repo and run `pip install -r requirements.txt`.
2. User the `generate_config.py` to create the spot fleet configuraiton json.

##Options
```
  --layer-id TEXT              Layer ID to add the Spot Fleet instances to.                [required]
  --region TEXT                Region Name to create the Spot Fleet (Default: us-west-2)   [required]
  --ami-id TEXT                AMI to launch. Default is Ubuntu 14.04 LTS                  [required]
  --ssh-key TEXT               SSH Key Name for the instances                              [required]
  --subnet-ids TEXT            Subnets to launch the AMI -- Specify multipe times
  --instance-types TEXT        Instance Types to launch - Specify multiple times           [required]
  --iam-fleet-role TEXT        IAM SpotFleet Rolei ARN                                     [required]
  --iam-instance-profile TEXT  EC2 IAM Instance Profile ARN                                [required]
  --security-group-ids TEXT    Security Groups for the instances -- Specify mutiple times  [required]
  --spot-price INTEGER         Maximum Spot Price in % of on-Demand                        [required]
  --help                       Show this message and exit.
```

##Example
```
./generate-config.py \
--layer-id 00000000-x0x0-000x-x000-x0xxx0x0x0x0 \
--ssh-key ssh_key \
--subnet-ids subnet-xxxxxxxx --subnet-ids subnet-yyyyyyyy --subnet-ids subnet-zzzzzzzz \
--instance-types c3.large --instance-types c4.large \
--iam-fleet-role 'arn:aws:iam::0000000000:role/aws-ec2-spot-fleet-role' \
--iam-instance-profile 'arn:aws:iam::0000000000:instance-profile/aws-opsworks-ec2-role' \
--spot-price 50  \
--security-group-ids sg-xxxxxxxx --security-group-ids sg-yyyyyyyy --security-group-ids sg-zzzzzzzz
```

This generates the `config.json` with `user-data` that will auto-register to the specified `layer-id` and deregister by watchng the termination notices every 5 seconds
###user-data register
```
opsworks_instance_id=$(aws opsworks register  --region us-east-1 --infrastructure-class ec2   --stack-id ${stackid}  --override-hostname $hostname --use-instance-profile  --local 2>&1 |grep -o 'Instance ID: .*' |cut -d' ' -f3)
aws opsworks wait instance-registered --region us-east-1 --instance-id $opsworks_instance_id
aws opsworks --region us-east-1 assign-instance --instance-id  $opsworks_instance_id --layer-ids $layerid
```
###user-data de-register
```
#!/bin/bash
while sleep 5
  do
    if curl --output /dev/null --silent --head --fail http://169.254.169.254/latest/meta-data/spot/termination-time
      then
        aws opsworks --region us-east-1 deregister-instance --instance-id $opsworks_instance_id
      fi
  done
EOF
chmod +x /usr/local/bin/spot-terminate
cat <<EOF >> /etc/supervisor/conf.d/spot-terminate.conf
[program:spot-terminate]
command=/usr/local/bin/spot-terminate
EOF
service supervisor restart
```

The user data also installs `supervisor`, `awscli` and `jq`. Supervisor runs the watcher script as daemon and de-regiater when it gets the `termiantion-noptice` from AWS Spot.

The `deregister` also happens on sclae in of the spot fleet.
