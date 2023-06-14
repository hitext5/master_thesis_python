from policies.electronic_devices_general import eval_policy_solar_panel


def eval_policy_machine_clean(requesting_device, collection):
    return requesting_device["last_cleaning"] < 4


sub_policies_dict = {
    'mandatory': [eval_policy_solar_panel],
    'double_check': [eval_policy_machine_clean],
    'optional': []
}

actions_dict = {}
