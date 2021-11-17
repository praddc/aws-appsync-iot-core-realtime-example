# process.env.AWS_SDK_LOAD_CONFIG = true;

# const AWS = require('aws-sdk');
# const fs = require('fs').promises;

# //if a region is not specified in your local AWS config, it will default to us-east-1
# const REGION = AWS.config.region || 'us-east-1';

# //if you wish to use a profile other than default, set an AWS_PROFILE environment variable when you run this app
# //for example:
# //AWS_PROFILE=my-aws-profile node create-sensor.js
# const PROFILE = process.env.AWS_PROFILE || 'default';

# //constants used in the app - do not change
# const SETTINGS_FILE = './settings.json';
# const MOBILE_SETTINGS_FILE = '../mobile/src/settings.json';

# //open sensor definition file
# var settings = require(SETTINGS_FILE);
# var mobileSettings = require(MOBILE_SETTINGS_FILE);

# //use the credentials from the AWS profile
# var credentials = new AWS.SharedIniFileCredentials({profile: PROFILE});
# AWS.config.credentials = credentials;

# AWS.config.update({
#     region: REGION
# });

import boto3
from botocore.config import Config
import datetime
import json
import os
import traceback

REGION = "us-west-2"
PROFILE = "pradulovic"

SETTINGS_FILE = "./settings.json"
MOBILE_SETTINGS_FILE = "../mobile/src/settings.json"
CERT_FOLDER = "./certs/"
POLICY_FILE = "./policy.json"
ROOT_CA_FILE = "AmazonRootCA1.pem"


def deleteSensor():
    try:

        session = boto3.session.Session(profile_name=PROFILE, region_name=REGION)
        client = session.client("iot")

        settings_file = open(SETTINGS_FILE, "r")
        settings = json.load(settings_file)
        settings_file.close()

        mobile_settings_file = open(MOBILE_SETTINGS_FILE, "r")
        mobileSettings = json.load(mobile_settings_file)
        mobile_settings_file.close()

        print(settings)

        # detach thing to certificate
        print("Detatching Thing Principal")
        response = client.detach_thing_principal(
            thingName=settings["clientId"], principal=settings["certificateArn"]
        )

        # delete the thing
        print("Deleting Thing")
        response = client.delete_thing(thingName=settings["clientId"])

        # detach policy from certificate
        print("Detatching Policy from Cert")
        myPolicyName = f"Policy-{settings['clientId']}"
        response = client.detach_policy(
            policyName=myPolicyName, target=settings["certificateArn"]
        )

        # delete the IOT policy
        print("Deleting Policy")
        response = client.delete_policy(policyName=myPolicyName)

        print("Deleting the Cert")
        # delete the certificates
        certificate = settings["certificateArn"].split("/")[1]
        response = client.update_certificate(
            certificateId=certificate, newStatus="INACTIVE"
        )
        response = client.delete_certificate(
            certificateId=certificate, forceDelete=True
        )
        settings["certificateArn"] = ""

        # delete the certificate files
        os.remove(settings['keyPath'])
        settings["keyPath"] = ""

        os.remove(settings['certPath'])
        settings["certPath"] = ""
        settings["caPath"] = ""

        # save the updated settings file
        # remove the iot core endpoint and clientId
        settings["host"] = ""
        settings["clientId"] = ""

        print("Updating Settings files")
        # save the updated settings file
        f = open(SETTINGS_FILE, "w")
        f.write(json.dumps(settings))
        f.close()

        # save the updated mobile settings file
        mobileSettings["sensorId"] = ""
        f = open(MOBILE_SETTINGS_FILE, "w")
        f.write(json.dumps(mobileSettings))
        f.close()

        # display results
        print("IoT Things Removed")
        print("AWS Region: " + REGION)
        print("AWS Profile: " + PROFILE)

    except Exception as err:
        traceback.print_tb(err.__traceback__)


if __name__ == "__main__":
    # print("Yay")
    deleteSensor()
