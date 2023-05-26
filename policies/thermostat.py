def eval_policy_ac_on(requesting_device, collection):
    # Retrieve thermostat data from database
    weather_station = collection.find_one({"device_id": "weather_station"})

    # Retrieve smartphone data from database
    smartphone = collection.find_one({"device_id": "smartphone"})

    # Check if the temperature outside is lower than the temperature inside and the air conditioner is on
    # and the user is at home
    return weather_station["temperature"] < requesting_device["temperature"] and \
        requesting_device["ac_on"] and smartphone["at_home"]


def eval_policy_heating_on(requesting_device, collection):
    # Retrieve thermostat data from database
    weather_station = collection.find_one({"device_id": "weather_station"})

    # Check if the temperature outside is lower than the temperature inside and the heating is on
    return weather_station["temperature"] < requesting_device["temperature"] and requesting_device["heating_on"]


def eval_policy_air_quality(requesting_device, collection):
    # Retrieve smartphone data from database
    smartphone = collection.find_one({"device_id": "smartphone"})

    return requesting_device["air_quality"] > 100 and smartphone["at_home"]


sub_policies_dict = {
    'mandatory': [],
    'double_check': [eval_policy_ac_on, eval_policy_heating_on, eval_policy_air_quality],
    'optional': []
}

actions_dict = {'eval_policy_ac_on': [{'device': 'window', 'to_do': 'open_window'},
                                      {'device': 'thermostat', 'to_do': ['turn_heating_on', 'ac_off']}],
                'eval_policy_heating_on': [{'device': 'window', 'to_do': 'close_window'}],
                'eval_policy_air_quality': [{'device': 'window', 'to_do': 'open_window'},
                                            {'device': 'thermostat', 'to_do': 'turn_fan_on'}]}
# Multiple actions for one device like this {'device': 'thermostat', 'to_do': ['ac_off', 'fan_on']}
# Another options is {'device': 'thermostat', 'to_do': 'ac_off'}, {'device': 'thermostat', 'to_do': 'fan_on'}
# But method add_policy_actions() in main.py should be modified accordingly
