from policies.carbon_monoxide_detector import eval_policy_gas_detected


def eval_policy_owner_away(requesting_device, collection):
    return not requesting_device['at_home'] and not eval_policy_gas_detected(requesting_device, collection)


sub_policies_dict = {
    'mandatory': [eval_policy_owner_away],
    'double_check': [],
    'optional': [],
}

actions_dict = {
    'eval_policy_owner_away': [
        {'device': 'window', 'to_do': 'close_window'},
    ],
}
