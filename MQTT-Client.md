### Callattendant MQTT client

Base-topic default is **callattendant**. Indicator names/subtopics are one of:<br>
&nbsp;&nbsp;&nbsp;&nbsp;`RING, Approved, Blocked, Message, MessageCount`

`CallerID` is a separate subtopic and does not have a hardware/GPIO equivalent indicator.

Examples:
```
callattendant/Approved {"TimeStamp": 1714510621, "State": "BLINK", "Period": 700, "Count": 2}
callattendant/CallerID {"TimeStamp": 1714512345, "Number": 6175551234, "Name": Unknown, "Action": "Screened", "Reason": "")
```
JSON formatted messages:

-    `TimeStamp` is either Unix epoch (seconds) or localtime as text.
-    `CallerID Number` can be either direct from provider or formatted for display.

Callattendant MQTT message templates:

**IndicatorName**: {"TimeStamp": 0, "State": "", "Period": 0, "Count": 0}

- Period := time period in ms
- Count := Number of cycles (Period * Count)
- State := ON, OFF, CLOSED, BLINK, PULSE or count of messages

**CallerID**: {"TimeStamp": 0, "Number": "", "Name": "", "Action": "", "Reason": ""} 

- Number may be raw/internal or formatted text.

Config file additions:
```
#MQTT_TIME_FORMAT: The format of the timestamp in the MQTT message. Valid values are: ISO, UNIX
# ISO = "YYYY-MM-DD HH:MM:SS"
# UNIX = Seconds since epoch (Usually: 1970-01-01 00:00:00)
MQTT_TIME_FORMAT = "UNIX"
#MQTT_CALLERID_FORMAT: The format of the callerid in the MQTT message. Valid values are: RAW, DISPLAY
# DISPLAY uses the PHONE_DISPLAY_FORMAT to format the number
# RAW uses the number from the provider
MQTT_CALLERID_FORMAT = "RAW"
# MQTT_NOTIFICATION_TYPE: The type of notification to send. Valid values are: EVENT, STATE
# This setting controls the RETAIN attribute of MQTT messages.
#   EVENT: Indicator topics are not retained
#   STATE: Indicator topics are retained 
MQTT_INDICATOR_TYPE = "STATE"
```
