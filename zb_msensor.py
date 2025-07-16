#!/usr/bin/env python3
#    The MIT License (MIT)
#    Copyright (c) Kiyo Chinzei (kchinzei@gmail.com)
#    Permission is hereby granted, free of charge, to any person obtaining a copy
#    of this software and associated documentation files (the "Software"), to deal
#    in the Software without restriction, including without limitation the rights
#    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#    copies of the Software, and to permit persons to whom the Software is
#    furnished to do so, subject to the following conditions:
#    The above copyright notice and this permission notice shall be included in
#    all copies or substantial portions of the Software.
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#    THE SOFTWARE.

REQUIRED_PYTHON_VERSION = (3, 9) # my raspi cannot go up 3.10.
import json
import argparse
import sys
import time
import paho.mqtt.client as mqtt

defaultHost = '192.168.0.201'
defaultPort = 1883
deviceState = {}
sensorSec = 0 # When a motion sensor raises a message, uppdate it.

kSleepSec = 10
kMSensorDict = {'topic_sub': 'zigbee2mqtt/MotionS/', 'message': 'occupancy'}
kTopicsDictList = [
    {'topic_sub': 'zigbee2mqtt/RGBWW', 'type': 'rgbww', 'topic_pub_x': '/set', 'offmsg': '{"state":"OFF"}'},
    {'topic_sub': 'zigbee2mqtt/WW_U', 'type': 'ww', 'topic_pub_x': '/set', 'offmsg': '{"state":"OFF"}'},
    {'topic_sub': 'zigbee2mqtt/WW_L', 'type': 'ww', 'topic_pub_x': '/set', 'offmsg': '{"state":"OFF"}'},
    {'topic_sub': 'wled/1cc53a', 'type': 'wled', 'topic_pub_x': '', 'offmsg': 'OFF'}
]

kSensorDictList = [
    {'topic_sub': 'zigbee2mqtt/MotionS', 'type': 'sonoff', 'key':'occupancy'},
]

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, reason_code, properties):
    print(f'Connected with result code {reason_code}', flush=True)
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    for d in kTopicsDictList:
        client.subscribe(d['topic_sub']+'/#')
    for d in kSensorDictList:
        client.subscribe(d['topic_sub']+'/#')

    # Populate deviceState
    for d in kTopicsDictList:
        deviceState[d['topic_sub']] = d['offmsg']

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global deviceState, sensorSec
    currentSec = time.time()
    # which topic we receive?
    for sensor in kSensorDictList:
        #print(f'{time.ctime()}: {msg.topic=}')
        if sensor['topic_sub'] == msg.topic:
            # Sensor issued a message.
            payload = json.loads(msg.payload.decode(encoding='utf-8'))
            occupancy = payload['occupancy']
            sensorSec = currentSec
            for d in kTopicsDictList:
                topic = d['topic_sub']
                topic_pub = topic + d['topic_pub_x']
                msg = deviceState[topic] if occupancy else d['offmsg']
                client.publish(topic=topic_pub, payload=msg, qos=1)
                print(f'{occupancy=} {topic_pub=} {msg=}', file=sys.stderr)
    if currentSec > sensorSec + kSleepSec:
        for d in kTopicsDictList:
            if d['topic_sub'] == msg.topic:
                deviceState[msg.topic] = msg.payload.decode(encoding='utf-8')
    

def zigbee_msensor(host, port, username, password):
    try:
        mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        mqttc.on_connect = on_connect
        mqttc.on_message = on_message
        mqttc.username_pw_set(username=username, password=password)
        mqttc.connect(host=host, port=port, keepalive=60)

        # Blocking call that processes network traffic, dispatches callbacks and handles reconnecting.
        mqttc.loop_forever()
    except KeyboardInterrupt:
        print('\n❌ Interrupted by user.', flush=True)
    except Exception as e:
        print(f'Unexpected error: {e}', file=sys.stderr)
    finally:
            mqttc.disconnect()
            print('MQTT client disconnected gracefully.', flush=True)


def main(argv=None):
    if sys.version_info < REQUIRED_PYTHON_VERSION:
        print(f'Requires python {REQUIRED_PYTHON_VERSION} or newer.', file=sys.stderr)
        return 1

    parser = argparse.ArgumentParser(description='Turn off / resume Zigbee devices by motion sensor')

    required_parser = parser.add_argument_group('required arguments')
    required_parser.add_argument('-u', '--username', metavar='user', type=str, required=True, help=f'username for MQTT host to publish')
    required_parser.add_argument('-p', '--password', metavar='pwd', type=str, required=True, help=f'password for MQTT user')
    parser.add_argument('-H', '--host', metavar='host', type=str, default=defaultHost, help=f'MQTT host (default: {defaultHost})')
    parser.add_argument('-P', '--port', metavar='port', type=int, default=defaultPort, help=f'MQTT port (default: {defaultPort})')
    
    args = parser.parse_args(args=argv)
    zigbee_msensor(**vars(args))
    return 0

if __name__ == '__main__':
    sys.exit(main())
