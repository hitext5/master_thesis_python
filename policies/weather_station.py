def eval_policy_outside_lower(requesting_device, collection):
    # Retrieve thermostat data from database
    thermostat = collection.find_one({"device_id": "thermostat"})

    # Retrieve smartphone data from database
    smartphone = collection.find_one({"device_id": "smartphone"})

    # Check if the temperature outside is lower than the temperature inside and the air conditioner is on
    # and the user is at home
    return requesting_device["temperature"] < thermostat["temperature"] and \
        thermostat["ac_on"] and smartphone["at_home"]


sub_policies_dict = {
    'mandatory': [],
    'double_check': [eval_policy_outside_lower]
}

actions_dict = {
    'eval_policy_outside_lower': [
        {'device': 'window', 'to_do': 'open_window'},
        # TODO either  {'device': 'thermostat', 'to_do': 'ac_off'},
        #  {'device': 'thermostat', 'to_do': 'fan_on'}
        #  or {'device': 'thermostat', 'to_do': ['ac_off', 'fan_on']}
        {'device': 'thermostat', 'to_do': 'ac_off'}
    ]
}
