def eval_washer_policies(requesting_device, collection):
    # def eval_policy_solar_panel():
    # Retrieve solar panel data from database
    solar_panel = collection.find_one({"device_id": "solar_panel"})

    # Retrieve all devices powered by solar panel
    powered_devices = collection.find({"powered_by": "solar_panel"})
    devices_list = list(powered_devices)

    total_power = sum(device["work_power"] for device in powered_devices)
    return solar_panel["provided_power"] >= total_power + requesting_device.work_power
