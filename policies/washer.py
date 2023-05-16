def eval_policy_solar_panel(requesting_device, collection):
    # Retrieve solar panel data from database
    solar_panel = collection.find_one({"device_id": "solar_panel"})

    # Retrieve all devices powered by solar panel
    powered_devices = collection.find({"powered_by": "solar_panel"})

    total_power = sum(device["work_power"] for device in powered_devices)

    return solar_panel["provided_power"] >= total_power + requesting_device["work_power"]


sub_policies = {
    'mandatory': [eval_policy_solar_panel],
    'double_check': []
}
