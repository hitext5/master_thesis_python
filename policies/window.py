def eval_window_policies(requesting_device, collection):
    sub_policies = {
        'mandatory': [],
        'double_check': []
    }

    # Execute high priority sub_policies
    for policy in sub_policies['mandatory']:
        if not policy(requesting_device, collection):
            return [False, "mandatory"]

    # Execute low priority sub_policies
    for policy in sub_policies['double_check']:
        if not policy(requesting_device, collection):
            return [False, "double_check"]

    return [True, "N/A"]

