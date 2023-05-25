def eval_policy_owner_home(requesting_device, collection):
    return requesting_device["at_home"]


sub_policies_dict = {
    'mandatory': [eval_policy_owner_home],
    'double_check': [],
    'optional': []
}

actions_dict = {
    'eval_policy_owner_home': [{'device': 'window', 'to_do': 'close_window'}]
}
