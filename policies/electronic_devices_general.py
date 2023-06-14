def eval_policy_solar_panel(requesting_device, collection):
    # Retrieve solar panel data from database
    solar_panel = collection.find_one({"device_type": "solar_panel"})
    # Retrieve all devices powered by the solar panel
    powered_devices = collection.find({"powered_by": "solar_panel"})
    # Evaluate the total power of all devices powered by the solar panel
    total_power = sum(device["work_power"] for device in powered_devices)
    # Check if the solar panel can provide enough power for the requesting device
    return solar_panel["provided_power"] >=\
        total_power + requesting_device["work_power"]
