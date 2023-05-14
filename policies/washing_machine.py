# TODO Make eval_policy_solar_panel a generic policy that can be used by any device that is powered by solar panel
def eval_washing_machine_policies(requesting_device, collection):
    sub_policies = {
        'mandatory': [eval_policy_solar_panel],
        'double_check': [eval_policy_machine_unclean]
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


def eval_policy_solar_panel(requesting_device, collection):
    # Retrieve solar panel data from database
    solar_panel = collection.find_one({"device_id": "solar_panel"})

    # Retrieve all devices powered by solar panel
    powered_devices = collection.find({"powered_by": "solar_panel"})

    total_power = sum(device["work_power"] for device in powered_devices)

    return solar_panel["provided_power"] >= total_power + requesting_device["work_power"]


def eval_policy_machine_unclean(requesting_device, collection):
    return requesting_device["last_cleaning"] < 4
