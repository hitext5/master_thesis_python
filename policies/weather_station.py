def eval_policy_rain_detected(requesting_device, collection):
    return requesting_device["rain_sensor"]


def eval_policy_wind_detected(requesting_device, collection):
    return requesting_device["wind_speed"] > 10


policies_dict = {
    'mandatory': [],
    'double_check': [eval_policy_rain_detected, eval_policy_wind_detected],
    'optional': []
}

actions_dict = {
    'eval_policy_rain_detected': [{'device': 'window', 'to_do': 'close_window'}],
    'eval_policy_wind_detected': [{'device': 'window', 'to_do': 'close_window'}]
}
