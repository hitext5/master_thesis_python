def eval_policy_gas_detected(requesting_device, collection):
    return requesting_device["gas_level"] > 30


policies_dict = {
    'mandatory': [eval_policy_gas_detected],
    'double_check': [],
    'optional': []
}

considerations_dict = {}

actions_dict = {
    'eval_policy_gas_detected': [{'device': 'window', 'to_do': 'open_window'},
                                 {'device': 'gas_valve', 'to_do': 'turn_off'}]
}
