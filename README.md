# zb_msensor

Turn off / resume Zigbee devices by PIR motion sensor.

### required arguments
- **-u user, --username user**
  username for MQTT host to publish
- **-p pwd, --password pwd**
  password for MQTT user

### optional arguments:
- **-h, --help**            show this help message and exit
- **-H host, --host host**  MQTT host (default: 192.168.0.201)
- **-P port, --port port**  MQTT port (default: 1883)

## What it is for?

This mini project is to use PIR (passive infrared) motion sensor to turn off / resume on smart bulbs.
Other devices like fan can be also controlled.

I use [Sonoff SNZB-03](https://www.zigbee2mqtt.io/devices/SNZB-03.html#sonoff-snzb-03) as a PIR sensor.

`zb_msensor` continuously monitors the state of bulbs to control.
When the PIR sensor detects human leaves, it turns off the bulbs.
When it detects enters, it resumes the previous state of the bulbs.
Since `zb_msensor` monitors the commands to these bulbs, it can flexibly update its state.

### 'Do not disturb' switch

Turn off period is hardcoded by the sensor, which is 1 minute.
When it does not detect a moving body in this period,
it turns off regardless someone is there or not.

To disable this behavior, another Zigbee switch can send 'do not disturb'
signals.

- Single press: 15 min
- Double press: 30 min
- Long press: toggle forever / cancel forever

I use [Aqara WXKG11LM](https://www.zigbee2mqtt.io/devices/WXKG11LM.html#aqara-wxkg11lm) as the switch.

## Dependency

- Python 3.9 or later
- [paho MQTT client](https://pypi.org/project/paho-mqtt/) `pip3 install paho-mqtt`
