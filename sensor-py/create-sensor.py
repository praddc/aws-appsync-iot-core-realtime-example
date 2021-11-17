# process.env.AWS_SDK_LOAD_CONFIG = true;

# const AWS = require('aws-sdk');
# const fs = require('fs').promises;
import boto3
from botocore.config import Config
import datetime
import json

# //if a region is not specified in your local AWS config, it will default to us-east-1
# const REGION = AWS.config.region || 'us-east-1';

REGION = "us-west-2"
PROFILE = "pradulovic"

# //if you wish to use a profile other than default, set an AWS_PROFILE environment variable when you run this app
# //for example:
# //AWS_PROFILE=my-aws-profile node create-sensor.js
# const PROFILE = process.env.AWS_PROFILE || 'default';

SETTINGS_FILE = "./settings.json"
MOBILE_SETTINGS_FILE = "../mobile/src/settings.json"
CERT_FOLDER = "./certs/"
POLICY_FILE = "./policy.json"
ROOT_CA_FILE = "AmazonRootCA1.pem"

# //open sensor definition file
# var settings = require(SETTINGS_FILE);
# var mobileSettings = require(MOBILE_SETTINGS_FILE);

# const policyDocument = require(POLICY_FILE);

# //use the credentials from the AWS profile
# var credentials = new AWS.SharedIniFileCredentials({profile: PROFILE});
# AWS.config.credentials = credentials;

# AWS.config.update({
#     region: REGION
# });

settings = {
    "host": "",
    "keyPath": "",
    "certPath": "",
    "caPath": "",
    "clientId": "",
    "certificateArn": "",
}

mobileSettings = {"sensorId": ""}

policyDoc = {
    "Version": "2012-10-17",
    "Statement": [
        {"Effect": "Allow", "Action": "iot:Connect", "Resource": "*"},
        {"Effect": "Allow", "Action": "iot:Receive", "Resource": "*"},
        {"Effect": "Allow", "Action": "iot:Subscribe", "Resource": "*"},
        {"Effect": "Allow", "Action": "iot:Publish", "Resource": "*"},
    ],
}


def createSensor():

    uid = int(datetime.datetime.now().timestamp() * 1000)
    settings["clientId"] = f"sensor-{uid}"

    session = boto3.session.Session(profile_name=PROFILE, region_name=REGION)
    client = session.client("iot")

    print("Describing Endpoing")
    response = client.describe_endpoint(endpointType="iot:Data-ATS")
    host = response["endpointAddress"]
    settings["host"] = host

    print("Updating Indexing Configuration")
    response = client.update_indexing_configuration(
        thingIndexingConfiguration={"thingIndexingMode": "REGISTRY_AND_SHADOW"}
    )

    print("Creating Policy")
    policyName = f"Policy-{settings['clientId']}"
    response = client.create_policy(
        policyName=policyName,
        policyDocument=json.dumps(policyDoc),
    )

    print("Creating Keys and Certificate")
    response = client.create_keys_and_certificate(setAsActive=True)
    settings["certificateArn"] = response["certificateArn"]
    certificateArn = response["certificateArn"]
    certificatePem = response["certificatePem"]
    privateKey = response["keyPair"]["PrivateKey"]

    # save the certificate
    filename = f"{CERT_FOLDER}{settings['clientId']}-certificate.pem.crt"
    settings["certPath"] = filename
    f = open(filename, "w")
    f.write(certificatePem)
    f.close()

    # save the private key
    filename = f"{CERT_FOLDER}{settings['clientId']}-private.pem.key"
    settings["keyPath"] = filename
    f = open(filename, "w")
    f.write(privateKey)
    f.close()

    # save the AWS root certificate
    settings["caPath"] = f"{CERT_FOLDER}{ROOT_CA_FILE}"

    # create the thing
    print("Creating Thing")
    response = client.create_thing(
        thingName=settings["clientId"],
    )

    # attach policy to certificate
    print("Attaching Policy")
    response = client.attach_policy(policyName=policyName, target=certificateArn)

    # attach thing to certificate
    print("Attaching Thing Principal")
    response = client.attach_thing_principal(
        thingName=settings["clientId"], principal=certificateArn
    )

    # save the updated settings file
    f = open(SETTINGS_FILE, "w")
    f.write(json.dumps(settings))
    f.close()

    # save the updated mobile settings file
    mobileSettings["sensorId"] = settings["clientId"]
    f = open(MOBILE_SETTINGS_FILE, "w")
    f.write(json.dumps(mobileSettings))
    f.close()

    # display results
    print(f"AWS Region: {REGION}")
    print(f"AWS Profile: {PROFILE}")
    print(f"IoT Thing Provisioned: {settings['clientId']}")


if __name__ == "__main__":
    # print("Yay")
    createSensor()
