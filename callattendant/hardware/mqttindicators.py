#!/usr/bin/python
# -*- coding: UTF-8 -*-
#
#  mqttindicators.py
#
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.


import time
import threading
import queue
import json

import paho.mqtt.client as mqtt
from common.utils import format_phone_no

# Client singleton
mqtt_client = None
class MQTTIndicatorClient(object):
    """
    Class for controlling the MQTT client.
    """
    def __init__(self, config):
        global mqtt_client
        if mqtt_client is None:
            # No need to re-init
            mqtt_client = self
            self.config = config
            # Check for callback API version (new in v2)
            self.has_callback_version = hasattr(mqtt, 'CallbackAPIVersion')
            self.server = self.config['MQTT_BROKER']
            self.port = self.config['MQTT_PORT']
            self.username = self.config['MQTT_USERNAME']
            self.password = self.config['MQTT_PASSWORD']
            # Formatting options
            self.time_format = self.config['MQTT_TIME_FORMAT']
            self.callerid_format = self.config['MQTT_CALLERID_FORMAT']
            # Retension option
            self.retain = True if self.config['MQTT_INDICATOR_TYPE'] == 'STATE' else False

            # Create client root name
            self.topic_prefix = self.config['MQTT_TOPIC_PREFIX'] + "/"
            # Create thread and queue for message publishing
            self.mqtt_queue = queue.Queue()
            self._thread = threading.Thread(
                target=self._mqtt_thread,
                kwargs={'mqtt_queue': self.mqtt_queue})
            self._thread.name = "mqtt_client"
            self._thread.start()

    def stop(self):
        """
        Stops the MQTT client publish thread
        """
        self.mqtt_queue.put(("STOP", None))
        self._thread.join()
    def _mqtt_thread(self, mqtt_queue):
        """
        Thread for handling MQTT messages.
        """
        while True:
            # Wait for a message to publish
            try:
                topic, message = mqtt_queue.get()
            except queue.Empty:
                continue

            # Exit thread if STOP message is received
            if topic == "STOP":
                break

            self.publish(topic, message)

    def queue_indicator(self, topic, state, period=0, count=0):
        """
        Queue a message to be published.
        """
        if (self.time_format == "ISO"):
            ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        else:
            ts = int(time.time())

        message = {}
        message['TimeStamp'] = ts
        message['State'] = state
        message['Period'] = period
        message['Count'] = count
        self.mqtt_queue.put_nowait((topic, json.dumps(message)))

    def queue_callerid(self, topic, name, number, action, reason):
        """
        Queue a message to be published.
        """
        if (self.time_format == "ISO"):
            ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        else:
            ts = int(time.time())

        displayNumber = number
        if (self.callerid_format == "DISPLAY"):
            displayNumber = format_phone_no(number, self.config)

        message = {}
        message['TimeStamp'] = ts
        message['Name'] = name
        message['Number'] = displayNumber
        message['Action'] = action
        message['Reason'] = reason
        self.mqtt_queue.put_nowait((topic, json.dumps(message)))

    def publish(self, topic, message):
        """
        Publish a message to a topic.
        """
        # Changes to the Paho MQTT client API in version 2.0
        # Even if we don't use callbacks, we need to specify the version
        if (self.has_callback_version):
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        else:
            # Version 1.x compatibility
            client = mqtt.Client()

        if self.username is not None:
            client.username_pw_set(self.username, self.password)
        client.connect(self.server, self.port)
        client.publish(self.topic_prefix + topic, message, retain=self.retain)
        client.disconnect()


class MQTTIndicator(object):
    """
    Class for controlling an MQTT LED topic
    """
    def __init__(self, topic, init_state='OFF'):
        self.topic = topic
        if mqtt_client is None:
            raise Exception("MQTT client not initialized")
        if init_state is not None:
            mqtt_client.queue_indicator(self.topic, init_state, 0, 0)
        self.blink_timer = None

    def turn_on(self):
        print("{} LED turned on".format(self.topic))
        if self.blink_timer is not None:
            self.blink_timer.cancel()
            self.blink_timer = None
        mqtt_client.queue_indicator(self.topic, "ON", 0, 0)

    def turn_off(self):
        print("{} LED turned off".format(self.topic))
        if self.blink_timer is not None:
            self.blink_timer.cancel()
            self.blink_timer = None
        mqtt_client.queue_indicator(self.topic, "OFF", 0, 0)

    def blink(self, max_times=10):
        # Just say we're blinking
        if max_times is None:
            print("{} LED blinking".format(self.topic))
            max_times = 0
        else:
            print("{} LED blinking: {} times".format(self.topic, max_times))
        mqtt_client.queue_indicator(self.topic, "BLINK", 700, max_times)
        if max_times > 0 and self.blink_timer is None:
            self.blink_timer = threading.Timer(0.7 * max_times, self.turn_off)
            self.blink_timer.start()

    def pulse(self, max_times=10):
        if max_times is None:
            print("{} LED pulsing".format(self.topic))
            max_times = 0
        else:
            print("{} LED pulsing: {} times".format(self.topic, max_times))
        mqtt_client.queue_indicator(self.topic, "PULSE", 2000, max_times)
        if max_times > 0 and self.blink_timer is None:
            self.blink_timer = threading.Timer(2.0 * max_times, self.turn_off)
            self.blink_timer.start()

    def close(self):
        if self.blink_timer is not None:
            self.blink_timer.cancel()
            self.blink_timer = None
        mqtt_client.queue_indicator(self.topic, "CLOSED", 0, 0)

class MQTTRingIndicator(MQTTIndicator):
    """
    Class for controlling the MQTT ring indicator.
    """
    def __init__(self):
        super().__init__("RING")

    def ring(self):
        super().blink()


class MQTTMessageIndicator(MQTTIndicator):
    """
    The message indicator activated when the voice messaging features are used.
    """
    def __init__(self):
        super().__init__('Messages', None)

    def blink(self):
        super().blink(max_times=None)   # None = forever

    def pulse(self):
        super().pulse(max_times=None)   # None = forever


class MQTTMessageCountIndicator(MQTTIndicator):
    """
    The message count indicator displays the number of unplayed messages in the system.
    """
    def __init__(self):
        super().__init__('MessageCount', None)
        self.dp = False
        self.count = 0

    @property
    def display(self):
        return self.count

    @display.setter
    def display(self, value):
        self.count = value
        print("{} indicator set to {}".format(self.topic, self.count))
        mqtt_client.queue_indicator(self.topic, value, 0, 0)

    @property
    def decimal_point(self):
        return self.dp

    @decimal_point.setter
    def decimal_point(self, value):
        self.dp = value

class MQTTCallerIdIndicator(MQTTIndicator):
    """
    The caller ID indicator displays the last caller ID received.
    """
    def __init__(self):
        super().__init__('CallerID', None)

    def display(self, name, number, action="Screened", reason=""):
        """
        Displays the last caller ID received.
        """
        mqtt_client.queue_callerid(self.topic, name, number, action, reason)
