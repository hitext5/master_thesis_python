from policies.carbon_monoxide_detector import eval_policy_gas_detected


def eval_policy_owner_away(requesting_device, collection):

    carbon_monoxide_detector = \
        collection.find_one({"device_type": "carbon_monoxide_detector"})

    # Check if the owner is away and there is no gas detected
    return not requesting_device['at_home'] and not \
        eval_policy_gas_detected(carbon_monoxide_detector, collection)


policies_dict = {
    'mandatory': [eval_policy_owner_away],
    'double_check': [],
    'optional': [],
}

actions_dict = {
    'eval_policy_owner_away': [
        {'device': 'window', 'to_do': 'close_window'},
    ],
}
