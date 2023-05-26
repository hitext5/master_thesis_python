import importlib

from flask import Flask, request, jsonify
from pymongo import MongoClient

atlas_uri = "mongodb://ReadOnlyUser:test456@ac-s2miieu-shard-00-00.s0mnged.mongodb.net:27017," \
            "ac-s2miieu-shard-00-01.s0mnged.mongodb.net:27017," \
            "ac-s2miieu-shard-00-02.s0mnged.mongodb.net:27017/?ssl=true&replicaSet=atlas-vihgip-shard-0" \
            "&authSource=admin&retryWrites=true&w=majority"
db_name = 'Cluster0'
mongo_client = MongoClient(atlas_uri)
database = mongo_client[db_name]
collection_devices = database["devices"]
collection_notifications = database["notifications"]

# If there is new policy file added, add it here as well
device_types = ['thermostat', 'washer', 'washing_machine', 'weather_station', 'window']
# Contains the policies for each device type separated by priority will be initialized in the following for loop
policies_dict = {}
# Contains the actions for each device type will be initialized in the following for loop
actions_dict = {}

# Contains the new policies that will be added to the database
new_policies = {}

# Dynamically import the policies and actions from the policy files
for device_type in device_types:
    module = importlib.import_module(f'policies.{device_type}')
    device_type_policies = getattr(module, 'sub_policies_dict')
    device_type_actions = getattr(module, 'actions_dict')
    policies_dict[device_type] = device_type_policies
    actions_dict[device_type] = device_type_actions

app = Flask(__name__)


# Call this function to evaluate the policies of a device type (default in message_handler)
@app.route('/check_policies/<string:device_type>', methods=['POST'])
def policy_result(device_type):
    data = request.get_json()
    # Retrieve the policies and actions of the requesting device type
    policy_of_requesting_device = policies_dict.get(device_type)
    actions_of_requesting_device = actions_dict.get(device_type)
    # Check if there is a policy for this device type
    if policy_of_requesting_device:
        result = evaluate_policies(policy_of_requesting_device, actions_of_requesting_device, data)
        # Send the result to the message_handler
        print(result)
        return jsonify({"result": result[0], "priority": result[1], "failed_sub_policies": result[2],
                        "actions": result[3]})
    else:
        print(f'No policy for {device_type}')
        # There is no policy for this device type
        return jsonify({"result": True})
        # return 'Invalid policy name', 400


# Call this function to add a new policy to a policy file
@app.route('/add_policy', methods=['POST'])
def add_policy():
    # Data provided by the web interface
    data = request.get_json()
    # priority is a string with the following format: 'mandatory' or 'double_check' or 'optional'
    priority = data['priority']
    # actions is a list with the following format: [{'device': 'window', 'to_do': 'close_window'}]
    actions = data['actions']
    # sub_policy_name is a string with the following format: 'eval_policy_owner_home'
    sub_policy_name = data['sub_policy_name']
    # sub policy code is a string with the following format:
    # ' return requesting_device["at_home"] and not eval_policy_gas_detected(requesting_device, collection)'
    sub_policy_code = data['sub_policy_code']
    # imports is a list with the following format:
    # ['from policies.carbon_monoxid_detector import eval_policy_gas_detected']
    imports = data['imports']
    # device_type is a string with the following format: 'smartphone'
    device_type = data['device_type']

    # Retrieve the sub_policies_dict and actions_dict from the module
    module = importlib.import_module(f'policies.{device_type}')
    sub_policies_dict = getattr(module, 'sub_policies_dict')
    actions_dict = getattr(module, 'actions_dict')

    # Retrieve the file content
    filename = f'{device_type}.py'
    with open(filename, 'r') as f:
        lines = f.readlines()

    # Find the index of the first blank line in the file
    blank_line_index = lines.index('\n')

    # Insert the new imports into the list of lines
    for imp in reversed(imports):
        lines.insert(blank_line_index, imp + '\n')

    # Insert a blank line to separate the imports from the function definition
    lines.insert(blank_line_index + len(imports), '\n')

    # Insert the function definition into the list of lines
    lines.insert(blank_line_index + len(imports) + 1, f'def {sub_policy_name}(requesting_device, collection):\n')

    # Insert the sub_policy_code into the list of lines, indented by 4 spaces
    lines.insert(blank_line_index + len(imports) + 2, '    ' + sub_policy_code + '\n')

    # Write the modified content back to the file
    with open(filename, 'w') as f:
        f.writelines(lines)

    # Update the new_policies dictionary when adding a new policy
    new_policies[device_type] = f'def {sub_policy_name}(requesting_device, collection):\n    {sub_policy_code}\n'

    # TODO Maybe introduce an if else statement to check if it is a sub policy for a
    #  single device type or multiple device types like electronic device applies to washing machine and washer
    # Add the sub_policy_name to the list of sub_policies for the specified priority
    # In order for getattr to work, the sub_policy_name must be the same as the method name, without def,
    #  and the method must already be defined in the policy file
    sub_policy = getattr(module, sub_policy_name)
    if sub_policy in sub_policies_dict[priority]:
        notification = {"message": f"The policy {sub_policy_name} already exists", "priority": priority}
        print(notification["message"])
        collection_notifications.insert_one(notification)
        return "Double entry", 400
    else:
        # Add the sub_policy to the list of sub_policies and the action to the list of actions
        sub_policies_dict[priority].append(sub_policy)
        actions_dict[sub_policy_name] = actions
        notification = {"message": f"The policy {sub_policy_name} has been added", "priority": priority}
        print(notification["message"])
        collection_notifications.insert_one(notification)
    return "Policies added but not updated yet"


# Call this function to get the pending new policies of a device type
@app.route('/pending_new_policies/<string:device_type>', methods=['GET'])
def pending_new_policies(device_type):
    return new_policies.get(device_type, "No new policies for this device type")


# TODO Add a method to delete a policy
# TODO Add a method to update a policy

# Call this function to get the sub_policies of a device type
@app.route('/get_sub_policies/<string:device_type>', methods=['GET'])
def get_sub_policies(device_type):
    module = importlib.import_module(f'policies.{device_type}')
    specific_policies = []
    general_policies = []
    for _, sub_policies in policies_dict[device_type].items():
        for sub_policy in sub_policies:
            if sub_policy.__module__ == module.__name__:
                specific_policies.append(sub_policy.__name__)
            else:
                general_policies.append(sub_policy.__name__)

    return jsonify({
        'specific_policies': specific_policies,
        'general_policies': general_policies
    })


# Call this function to update the policies_dict and actions_dict after a policy has been added
@app.route('/update_policies/<string:device_type>', methods=['PUT'])
def update_policies(device_type):
    # After a policy has been added, the policies_dict and actions_dict must be updated
    module = importlib.import_module(f'policies.{device_type}')
    device_type_policies = getattr(module, 'sub_policies_dict')
    device_type_actions = getattr(module, 'actions_dict')
    policies_dict[device_type] = device_type_policies
    actions_dict[device_type] = device_type_actions
    notification = {"message": f"The policies for {device_type} have been updated"}
    print(notification["message"])
    collection_notifications.insert_one(notification)
    new_policies.pop(device_type, None)
    return "Policies updated"


# Call this function when a policy failed and you want to get the actions that the device has to do
# (default in message_handler
@app.route('/failed_policy_actions', methods=['GET'])
def failed_policy_actions():
    # Get the list of failed sub-policies and the device type from the request parameters
    failed_sub_policies = request.args.getlist('failed_sub_policies')
    device_type = request.args.get('device_type')
    # List of actions that the device has to do
    policy_to_dos = []
    # Get the actions for the requesting device
    actions_of_requesting_device = actions_dict.get(device_type)
    # Iterate over the failed sub-policies
    for policy_name in failed_sub_policies:
        add_policy_actions(policy_name, actions_of_requesting_device, policy_to_dos)
    # Return the actions as a JSON response
    return jsonify({'actions': policy_to_dos})


def add_policy_actions(policy_name, possible_actions, policy_to_dos):
    # Check if the policy has actions
    if policy_name in possible_actions:
        # A policy can have multiple actions
        for action in possible_actions[policy_name]:
            device = action['device']
            to_do = action['to_do']
            # Check if the action is a list of actions (the device has to do multiple things)
            if isinstance(to_do, list):
                for single_action in to_do:
                    new_action = {'device': device, 'to_do': single_action}
                    # Check if the action is already in the list of actions
                    if new_action not in policy_to_dos:
                        policy_to_dos.append(new_action)
            else:
                new_action = {'device': device, 'to_do': to_do}
                # Check if the action is already in the list of actions
                if new_action not in policy_to_dos:
                    policy_to_dos.append(new_action)


def evaluate_policies(sub_policies, possible_actions, requesting_device):
    # Lists to store the failed sub_policies and the actions that need to be executed
    failed_sub_policies = []
    policy_to_dos = []

    # Execute high priority sub_policies
    for policy in sub_policies['mandatory']:
        result = policy(requesting_device, collection_devices)
        if not result:
            # If a high priority sub_policy fails, the other high priority sub_policies are not executed
            policy_to_dos = []
            return [False, "mandatory", failed_sub_policies, policy_to_dos]
        else:
            # If a high priority sub_policy succeeds, the actions of that sub_policy are added to the policy_to_dos
            policy_name = policy.__name__
            add_policy_actions(policy_name, possible_actions, policy_to_dos)

    # Execute double check sub_policies
    for policy in sub_policies['double_check']:
        result = policy(requesting_device, collection_devices)
        if not result:
            # If a double check sub_policy fails, the other low priority sub_policies are still executed
            # add the failed sub_policy to the list of failed sub_policies to double-check later
            failed_sub_policies.append(policy.__name__)
        else:
            # If a double check sub_policy succeeds, the actions of that sub_policy are added to the policy_to_dos
            policy_name = policy.__name__
            add_policy_actions(policy_name, possible_actions, policy_to_dos)

    # Execute low priority sub_policies
    for policy in sub_policies['optional']:
        result = policy(requesting_device, collection_devices)
        if result:
            # If a low priority sub_policy succeeds, the actions of that sub_policy are added to the policy_to_dos
            policy_name = policy.__name__
            add_policy_actions(policy_name, possible_actions, policy_to_dos)

    if failed_sub_policies:
        # If there are failed low priority sub_policies, the policy fails but the double check will be handled in
        #  the message_handler
        return [False, "double_check", failed_sub_policies, policy_to_dos]

    # If all sub_policies succeed, the policy succeeds
    return [True, "N/A", failed_sub_policies, policy_to_dos]


if __name__ == "__main__":
    app.run(port=8080)
