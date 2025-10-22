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
sleepPeriodSec = 0 # When a motion sensor raises a message, uppdate it.
cancelPeriodSec = 0

kSleepSec = 10
kCancelSec = 15*60
kCancelSec_inf = float('inf')

kTopicsDictList = [
#    {'topic_sub': 'zigbee2mqtt/RGBWW', 'type': 'rgbww', 'topic_pub_x': '/set', 'offmsg': '{"state":"OFF"}',
#     'query':'{"state":""}', 'topic_get': '/get'},
    {'topic_sub': 'zigbee2mqtt/WW_U', 'type': 'ww', 'topic_pub_x': '/set', 'offmsg': '{"state":"OFF"}',
     'query':'{"state":""}', 'topic_get': '/get'},
    {'topic_sub': 'zigbee2mqtt/WW_L', 'type': 'ww', 'topic_pub_x': '/set', 'offmsg': '{"state":"OFF"}',
     'query':'{"state":""}', 'topic_get': '/get'},
    {'topic_sub': 'wled/1cc53a', 'type': 'wled', 'topic_pub_x': '', 'offmsg': 'OFF'}
]

kSensorDictList = [
    {'topic_sub': 'zigbee2mqtt/MotionS', 'type': 'sonoff', 'key':'occupancy'},
]

kCancelDictList = [
    {'topic_sub': 'zigbee2mqtt/Aqara01', 'type': 'aqara', 'key':'action'},
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
    for d in kCancelDictList:
        client.subscribe(d['topic_sub']+'/#')

    # Populate deviceState
    for d in kTopicsDictList:
        deviceState[d['topic_sub']] = d['offmsg']
        query = d.get('query', None)
        if query is not None:
            client.publish(topic=d['topic_sub'] + d['topic_get'], payload=query)

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global deviceState, sleepPeriodSec, cancelPeriodSec
    currentSec = time.time()
    # which topic we receive?
    if currentSec > cancelPeriodSec:
        for sensor in kSensorDictList:
            # print(f'{time.ctime()}: {msg.topic=}')
            if sensor['topic_sub'] == msg.topic:
                # Sensor issued a message.
                payload = json.loads(msg.payload.decode(encoding='utf-8'))
                occupancy = payload['occupancy']
                sleepPeriodSec = currentSec + kSleepSec
                for d in kTopicsDictList:
                    topic = d['topic_sub']
                    topic_pub = topic + d['topic_pub_x']
                    payload_pub = deviceState[topic] if occupancy else d['offmsg']
                    if d['type'] == 'rgbww':
                        # 250719                                                          
                        # Miboxer FUT03xZ odd behavior
                        # 1) When turn on in RGBW mode, it always first turns on in color_temp mode (White on)
                        # 2) Moment after, it changes to xy mode, but in very dark brightness
                        # As workaround, first turn on with brightness=0, then send brightness alone.
                        # This still behaves odd as it momently turns off, but much better...
                        # https://github.com/Koenkk/zigbee2mqtt/issues/19345
                        # (transition has no effect for mine)
                        data = json.loads(msg.payload.decode(encoding='utf-8'))
                        # 1) Get the brightness value
                        brightness = data.get('brightness', 0)
                        # 2) Swap brightness value to 0 (redundant here, but assuming we want to set it anyway)
                        data['brightness'] = 0
                        # Convert back to JSON string
                        payload1 = json.dumps(data)
                        payload2 = f'{{"brightness":{brightness}}}'
                        client.publish(topic=topic_pub, payload=payload1)
                        client.publish(topic=topic_pub, payload=payload2)
                        time.sleep(2)
                        client.publish(topic=topic_pub, payload=payload2)
                    else:
                        client.publish(topic=topic_pub, payload=payload_pub)
                    print(f'{occupancy=} {topic_pub=} {payload_pub=}', file=sys.stderr)
    for cancel in kCancelDictList:
        if cancel['topic_sub'] == msg.topic:
            payload = json.loads(msg.payload.decode(encoding='utf-8'))
            action = payload.get(cancel['key'], '')
            if action == 'single':
                cancelPeriodSec = currentSec + kCancelSec
            if action == 'double':
                cancelPeriodSec = currentSec + kCancelSec * 2
            elif action == 'triple':
                cancelPeriodSec = currentSec + kCancelSec * 3
            elif action == 'hold':
                if cancelPeriodSec != kCancelSec_inf:
                    cancelPeriodSec = kCancelSec_inf
                else:
                    cancelPeriodSec = currentSec
            print(f'cancel switch {msg.topic} | action={action}', file=sys.stderr)√
    if currentSec > sleepPeriodSec:
        for d in kTopicsDictList:
            if d['topic_sub'] == msg.topic:
                deviceState[msg.topic] = msg.payload.decode(encoding='utf-8')
                # print(f'msg received= {deviceState[msg.topic]}')

def zigbee_msensor(host, port, username, password):
    try:
        mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
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
