# const awsIot = require('aws-iot-device-sdk');
import argparse
import json
import sys
import threading

from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder

# load the settings file that contains the location of the device certificates and the clientId of the sensor
SETTINGS_FILENAME = "./settings.json"
# var settings = require('./settings.json');


# constants used in the application
SHADOW_TOPIC = "$aws/things/[thingName]/shadow/update"
VALUE_TOPIC = "dt/sensor-view/[thingName]/sensor-value"  # topic to which sensor values will be published
VALUE_RATE = (
    2000  # rate in milliseconds new temperature values will be published to the Cloud
)

# //initialize the IOT device
# var device = awsIot.device(settings);

# //shadow document to be transmitted at statup
# var shadowDocument = {
#     state: {
#         reported: {
#             sensorType: "Temperature",
#         }
#     }
# }

# //create a placeholder for the message
# var msg = {
#     value: 0,
#     timestamp: new Date().getTime()
# }

# device.on('connect', function() {

#     console.log('connected to IoT Hub');

#     //publish the shadow document for the sensor
#     var topic = SHADOW_TOPIC.replace('[thingName]', settings.clientId);

#     device.publish(topic, JSON.stringify(shadowDocument));

#     console.log('published to shadow topic ' + topic + ' ' + JSON.stringify(shadowDocument));

#     //publish new value readings based on value_rate
#     setInterval(function(){

#         msg.value = 75 + Math.floor((Math.random() * (10 - 1) + 1));
#         msg.timestamp = new Date().getTime();

#         var topic = VALUE_TOPIC.replace('[thingName]', settings.clientId);

#         device.publish(topic, JSON.stringify(msg));

#         console.log('published to topic ' + topic + ' ' + JSON.stringify(msg));


#     }, VALUE_RATE);
# });

# device.on('error', function(error) {
#     console.log('Error: ', error);
# });

parser = argparse.ArgumentParser(
    description="Send and receive messages through and MQTT connection."
)
# parser.add_argument('--endpoint', required=True, help="Your AWS IoT custom endpoint, not including a port. " +
#                                                       "Ex: \"abcd123456wxyz-ats.iot.us-east-1.amazonaws.com\"")
# parser.add_argument('--port', type=int, help="Specify port. AWS IoT supports 443 and 8883.")
# parser.add_argument('--cert', help="File path to your client certificate, in PEM format.")
# parser.add_argument('--key', help="File path to your private key, in PEM format.")
# parser.add_argument('--root-ca', help="File path to root certificate authority, in PEM format. " +
#                                       "Necessary if MQTT server uses a certificate that's not already in " +
#                                       "your trust store.")
# parser.add_argument('--client-id', default="test-" + str(uuid4()), help="Client ID for MQTT connection.")
# parser.add_argument('--topic', default="test/topic", help="Topic to subscribe to, and publish messages to.")
# parser.add_argument('--message', default="Hello World!", help="Message to publish. " +
#                                                               "Specify empty string to publish nothing.")
# parser.add_argument('--count', default=10, type=int, help="Number of messages to publish/receive before exiting. " +
#                                                           "Specify 0 to run forever.")
# parser.add_argument('--use-websocket', default=False, action='store_true',
#     help="To use a websocket instead of raw mqtt. If you " +
#     "specify this option you must specify a region for signing.")
# parser.add_argument('--signing-region', default='us-east-1', help="If you specify --use-web-socket, this " +
#     "is the region that will be used for computing the Sigv4 signature")
# parser.add_argument('--proxy-host', help="Hostname of proxy to connect to.")
# parser.add_argument('--proxy-port', type=int, default=8080, help="Port of proxy to connect to.")
parser.add_argument(
    "--verbosity",
    choices=[x.name for x in io.LogLevel],
    default=io.LogLevel.NoLogs.name,
    help="Logging level",
)

# Using globals to simplify sample code
args = parser.parse_args()

io.init_logging(getattr(io.LogLevel, args.verbosity), "stderr")

received_count = 0
received_all_event = threading.Event()

# Callback when connection is accidentally lost.
def on_connection_interrupted(connection, error, **kwargs):
    print("Connection interrupted. error: {}".format(error))


# Callback when an interrupted connection is re-established.
def on_connection_resumed(connection, return_code, session_present, **kwargs):
    print(
        "Connection resumed. return_code: {} session_present: {}".format(
            return_code, session_present
        )
    )

    if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
        print("Session did not persist. Resubscribing to existing topics...")
        resubscribe_future, _ = connection.resubscribe_existing_topics()

        # Cannot synchronously wait for resubscribe result because we're on the connection's event-loop thread,
        # evaluate result with a callback instead.
        resubscribe_future.add_done_callback(on_resubscribe_complete)


def on_resubscribe_complete(resubscribe_future):
    resubscribe_results = resubscribe_future.result()
    print("Resubscribe results: {}".format(resubscribe_results))

    for topic, qos in resubscribe_results["topics"]:
        if qos is None:
            sys.exit("Server rejected resubscribe to topic: {}".format(topic))


# Callback when the subscribed topic receives a message
def on_message_received(topic, payload, dup, qos, retain, **kwargs):
    print("Received message from topic '{}': {}".format(topic, payload))
    global received_count
    received_count += 1
    if received_count == args.count:
        received_all_event.set()


if __name__ == "__main__":
    # Spin up resources
    event_loop_group = io.EventLoopGroup(1)
    host_resolver = io.DefaultHostResolver(event_loop_group)
    client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

    proxy_options = None

    settings_file = open(SETTINGS_FILENAME, "r")
    settings = json.load(settings_file)
    settings_file.close()

    mqtt_connection = mqtt_connection_builder.mtls_from_path(
        endpoint=settings["host"],
        port=443,
        cert_filepath=settings["certPath"],
        pri_key_filepath=settings["keyPath"],
        client_bootstrap=client_bootstrap,
        ca_filepath=settings["caPath"],
        on_connection_interrupted=on_connection_interrupted,
        on_connection_resumed=on_connection_resumed,
        client_id=settings["clientId"],
        clean_session=False,
        keep_alive_secs=30,
        http_proxy_options=proxy_options,
    )

    print(
        "Connecting to {} with client ID '{}'...".format(
            settings["host"], settings["clientId"]
        )
    )

    connect_future = mqtt_connection.connect()

    # Future.result() waits until a result is available
    connect_future.result()
    print("Connected!")

    # Subscribe
    print("Subscribing to topic '{}'...".format(args.topic))
    subscribe_future, packet_id = mqtt_connection.subscribe(
        topic=args.topic, qos=mqtt.QoS.AT_LEAST_ONCE, callback=on_message_received
    )

    subscribe_result = subscribe_future.result()
    print("Subscribed with {}".format(str(subscribe_result["qos"])))

    #
    #
    #

    # Disconnect
    print("Disconnecting...")
    disconnect_future = mqtt_connection.disconnect()
    disconnect_future.result()
    print("Disconnected!")
