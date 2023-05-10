def eval_washing_machine_policies(requesting_device, collection):
    sub_policies = {
        'high_priority': [eval_policy_solar_panel],
        'medium_priority': [],
        'low_priority': [eval_policy_machine_unclean]
    }

    # Execute high priority sub_policies
    for policy in sub_policies['high_priority']:
        if not policy(requesting_device, collection):
            return [False, "high_priority"]

    # Execute medium priority sub_policies
    for policy in sub_policies['medium_priority']:
        if not policy(requesting_device, collection):
            return [False, "medium_priority"]

    # Execute low priority sub_policies
    for policy in sub_policies['low_priority']:
        if not policy(requesting_device, collection):
            return [False, "low_priority"]

    return [True, "N/A"]


def eval_policy_solar_panel(requesting_device, collection):
    # Retrieve solar panel data from database
    solar_panel = collection.find_one({"device_id": "solar_panel"})

    # Retrieve all devices powered by solar panel
    powered_devices = collection.find({"powered_by": "solar_panel"})

    total_power = sum(device["work_power"] for device in powered_devices)

    return solar_panel["provided_power"] >= total_power + requesting_device["work_power"]


def eval_policy_machine_unclean(requesting_device, collection):
    print(requesting_device)
    return requesting_device["last_cleaning"] < 4
