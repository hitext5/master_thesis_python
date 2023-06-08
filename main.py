import importlib
import re
import sys

from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient, DESCENDING
from datetime import datetime

atlas_uri_admin = "mongodb://Kleriakanus:test123@ac-s2miieu-shard-00-00.s0mnged.mongodb.net:27017," \
                  "ac-s2miieu-shard-00-01.s0mnged.mongodb.net:27017," \
                  "ac-s2miieu-shard-00-02.s0mnged.mongodb.net:27017/?ssl=true&replicaSet=atlas-vihgip-shard-0" \
                  "&authSource=admin&retryWrites=true&w=majority"
atlas_uri_read = "mongodb://ReadOnlyUser:test456@ac-s2miieu-shard-00-00.s0mnged.mongodb.net:27017," \
                 "ac-s2miieu-shard-00-01.s0mnged.mongodb.net:27017," \
                 "ac-s2miieu-shard-00-02.s0mnged.mongodb.net:27017/?ssl=true&replicaSet=atlas-vihgip-shard-0" \
                 "&authSource=admin&retryWrites=true&w=majority"
rcbms_database_name = 'Cluster0'
policy_database_name = 'Policies'
mongo_client_admin = MongoClient(atlas_uri_admin)
mongo_client_read = MongoClient(atlas_uri_read)
# The policies work with the read-only access collection
device_database = mongo_client_read[rcbms_database_name]
# To insert the notifications in the device database and policies in the policy database we need admin access
notification_database = mongo_client_admin[rcbms_database_name]
policy_database = mongo_client_admin[policy_database_name]
collection_devices = device_database["devices"]
collection_notifications = notification_database["notifications"]

# If there is new policy file added, add it here as well
device_types = ['carbon_monoxide_detector', 'smartphone', 'thermostat', 'washer', 'washing_machine', 'weather_station',
                'window']
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
CORS(app, origins="http://localhost:5000")


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
        return jsonify({"result": result[0], "priority": result[1], "failed_double_check": result[2],
                        "actions": result[3]})
    else:
        # There is no policy for this device type
        return jsonify({"result": True})
        # return 'Invalid policy name', 400


# Call this function when a policy failed, and you want to get the actions that the device has to do
# (default in message_handler)
@app.route('/failed_policy_actions', methods=['GET'])
def failed_policy_actions():
    # Get the list of failed sub-policies and the device type from the request parameters
    failed_double_check = request.args.getlist('failed_double_check')
    device_type = request.args.get('device_type')
    # List of actions that the device has to do
    policy_to_dos = []
    # Get the actions for the requesting device
    actions_of_requesting_device = actions_dict.get(device_type)
    # Iterate over the failed sub-policies
    for policy_name in failed_double_check:
        add_policy_actions(policy_name, actions_of_requesting_device, policy_to_dos)
    # Return the actions as a JSON response
    return jsonify({'actions': policy_to_dos})


# Call this function to share a policy with the community
@app.route('/share_sub_policy/<string:device_type>/<string:sub_policy_name>', methods=['POST'])
def share_sub_policy(device_type, sub_policy_name):
    sub_policy_data = get_sub_policy_data(device_type, sub_policy_name)
    # Check if the sub-policy data is None
    if sub_policy_data is None:
        return 'Sub-policy not found', 404

    # Get the collection for the specified device type
    collection = policy_database[device_type]
    # Insert the policy data into the collection for the specified device type if it does not exist yet
    if collection.find_one({'sub_policy_name': sub_policy_name}):
        current_time = datetime.now().strftime('%H:%M:%S')
        current_date = datetime.now().strftime('%Y-%m-%d')
        notification = {"message": f"The policy {sub_policy_name} already exists",
                        "time": current_time,
                        "date": current_date
                        }
        collection_notifications.insert_one(notification)
        return 'Policy already exists', 400
    # Return a response indicating that the sub-policy was successfully inserted
    collection.insert_one(sub_policy_data)
    return 'Sub-policy inserted successfully', 201


# Call this function to add a new policy to a policy file (policies_dict and actions_dict have to be updated
# with the update_policies function after this function is called to make the new policy available at runtime)
@app.route('/add_sub_policy', methods=['POST'])
def add_sub_policy():
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

    result = update_policy_file(device_type=device_type,
                                priority=priority,
                                actions=actions,
                                sub_policy_name=sub_policy_name,
                                sub_policy_code=sub_policy_code,
                                imports=imports)

    if result:
        return "Policy added but not updated yet"
    else:
        return "Sub-policy already exists"


@app.route('/add_sub_policy_from_db/community/<string:device_type>/<string:sub_policy_name>', methods=['POST'])
def add_sub_policy_from_db(device_type, sub_policy_name):
    collection = policy_database[device_type]
    policy = collection.find_one({'sub_policy_name': sub_policy_name})
    if not policy:
        return "Sub-policy not found"

    priority = policy['priority']
    actions = policy['actions']
    sub_policy_name = policy['sub_policy_name']
    sub_policy_code = policy['sub_policy_code']
    imports = policy['imports']

    result = update_policy_file(device_type=device_type,
                                priority=priority,
                                actions=actions,
                                sub_policy_name=sub_policy_name,
                                sub_policy_code=sub_policy_code,
                                imports=imports)

    if result:
        return "Policy added but not updated yet"
    else:
        return "Sub-policy already exists"


# Call this function to get the pending new policies of a device type
@app.route('/pending_new_sub_policies/<string:device_type>', methods=['GET'])
def pending_new_sub_policies(device_type):
    return new_policies.get(device_type, "No new policies for this device type")


# Call this function to get the last 20 notifications
@app.route('/get_notifications', methods=['GET'])
def get_notifications():
    # Get the page number from the request parameters
    page = int(request.args.get('page', 1))
    # Number of notifications per page
    per_page = 20
    # Based on the page number, calculate the number of database entries to skip
    skip = (page - 1) * per_page
    # Get the last 20 notifications from the database and convert the ObjectId to a string
    notifications = collection_notifications.find().sort('_id', DESCENDING).skip(skip).limit(per_page)
    notifications = [{**doc, '_id': str(doc['_id'])} for doc in notifications]
    return jsonify(notifications)


# Call this function to get all the devices
@app.route('/get_devices', methods=['GET'])
def get_devices():
    devices = collection_devices.find()
    devices = [{**doc, '_id': str(doc['_id'])} for doc in devices]
    return jsonify(devices)


@app.route('/get_possible_actions/<string:device_type>', methods=['GET'])
def get_possible_actions(device_type):
    devices = collection_devices.find({'device_type': device_type}, {'possible_actions': 1})
    possible_actions = []
    for device in devices:
        if 'possible_actions' in device:
            possible_actions.extend(device['possible_actions'])
    return jsonify(list(set(possible_actions)))


# Call this function to delete a sub-policy from a policy file
@app.route('/delete_sub_policy/local/<string:device_type>/<string:sub_policy_name>', methods=['DELETE'])
def delete_sub_policy(device_type, sub_policy_name):
    module = importlib.import_module(f'policies.{device_type}')
    if not hasattr(module, 'sub_policies_dict'):
        return "Policy file not found"

    sub_policies_dict = getattr(module, 'sub_policies_dict')
    if sub_policy_name not in [sub_policy.__name__ for priority in sub_policies_dict for sub_policy in
                               sub_policies_dict[priority]]:
        return "Sub-policy not found"
    actions_dict = getattr(module, 'actions_dict')
    filename = f'policies/{device_type}.py'
    with open(filename, 'r') as f:
        lines = f.readlines()

    # Remove sub-policy from sub_policies_dict
    for priority in sub_policies_dict:
        if sub_policy_name in [sub_policy.__name__ for sub_policy in sub_policies_dict[priority]]:
            sub_policies_dict[priority] = [sub_policy for sub_policy in sub_policies_dict[priority] if
                                           sub_policy.__name__ != sub_policy_name]
            break

    # Remove actions from actions_dict
    if sub_policy_name in actions_dict:
        del actions_dict[sub_policy_name]

    # Update sub_policies_dict in file
    sub_policies_start_index = next(i for i, line in enumerate(lines) if line.startswith('sub_policies_dict'))
    sub_policies_end_index = next(
        i for i, line in enumerate(lines[sub_policies_start_index:], sub_policies_start_index) if
        line.startswith('}'))
    del lines[sub_policies_start_index:sub_policies_end_index + 1]
    new_sub_policies_lines = format_sub_policies_dict(sub_policies_dict).split('\n')
    for i, line in enumerate(new_sub_policies_lines):
        lines.insert(sub_policies_start_index + i, line + '\n')

    # Update actions_dict in file
    actions_start_index = next(i for i, line in enumerate(lines) if line.startswith('actions_dict'))
    actions_end_index = next(
        i for i, line in enumerate(lines[actions_start_index:], actions_start_index) if line.startswith('}'))
    del lines[actions_start_index:actions_end_index + 1]
    new_actions_lines = format_actions_dict(actions_dict).split('\n')
    for i, line in enumerate(new_actions_lines):
        lines.insert(actions_start_index + i, line + '\n')

    # Remove import statement from file
    imported_function_match = re.search(r'from .+ import (\w+)', ''.join(lines))
    if imported_function_match:
        imported_function_name = imported_function_match.group(1)
        import_pattern = re.compile(f'^from .* import {imported_function_name}$')
        import_index = next((i for i, line in enumerate(lines) if import_pattern.match(line)), None)
        if import_index is not None:
            del lines[import_index]

    # Remove sub-policy function from file
    function_start_pattern = re.compile(f'^def {sub_policy_name}\(')
    function_start_index = next((i for i, line in enumerate(lines) if function_start_pattern.match(line)), None)
    if function_start_index is not None:
        function_end_index = next(
            i for i, line in enumerate(lines[function_start_index + 1:], function_start_index + 1) if
            not line.startswith(' '))
        del lines[function_start_index:function_end_index]

    with open(filename, 'w') as f:
        f.writelines(lines)

    importlib.reload(module)

    return "Policy deleted"


# Call this function to delete a sub-policy from the database
@app.route('/delete_sub_policy/community/<string:device_type>/<string:sub_policy_name>', methods=['DELETE'])
def delete_sub_policy_from_db(device_type, sub_policy_name):
    collection = policy_database[device_type]
    result = collection.delete_one({'sub_policy_name': sub_policy_name})
    if result.deleted_count == 1:
        return "Sub-policy deleted"
    else:
        return "Sub-policy not found"


# Call this function to return a specific sub-policy entirely
@app.route('/change_sub_policy/local/<string:device_type>/<string:sub_policy_name>', methods=['GET'])
def change_sub_policy(device_type, sub_policy_name):
    sub_policy_data = get_sub_policy_data(device_type, sub_policy_name)
    if sub_policy_data is None:
        return 'Sub-policy not found', 404
    return jsonify(sub_policy_data)

# Call this function to return a specific sub-policy entry from the database entirely
@app.route('/change_sub_policy/community/<string:device_type>/<string:sub_policy_name>', methods=['GET'])
def change_sub_policy_community(device_type, sub_policy_name):
    collection = policy_database[device_type]

    # Query the database to find the sub-policy with the given sub-policy name
    sub_policy = collection.find_one({'sub_policy_name': sub_policy_name})
    if not sub_policy:
        return jsonify({'error': 'Sub-policy not found'})

    # Extract the sub-policy information from the database result
    priority = sub_policy['priority']
    actions = sub_policy['actions']
    sub_policy_name = sub_policy['sub_policy_name']
    sub_policy_code = sub_policy['sub_policy_code']
    imports = sub_policy['imports']

    return jsonify({
        'priority': priority,
        'actions': actions,
        'sub_policy_name': sub_policy_name,
        'sub_policy_code': sub_policy_code,
        'imports': imports,
        'device_type': device_type
    })


# Call this function to get the sub-policies for a device type from the database
@app.route('/get_sub_policies/community/<string:device_type>', methods=['GET'])
def get_sub_policies_community(device_type):
    collection = policy_database[device_type]
    policies = collection.find()
    policies = [{**doc, '_id': str(doc['_id'])} for doc in policies]
    return jsonify(policies)


# Call this function to get the code of a sub-policy of a device type from the database
@app.route('/sub_policy_details/community/<string:device_type>/<string:sub_policy_name>', methods=['GET'])
def sub_policy_details_community(device_type, sub_policy_name):
    collection = policy_database[device_type]
    sub_policy = collection.find_one({'sub_policy_name': sub_policy_name})
    if sub_policy:
        sub_policy_code = sub_policy.get('sub_policy_code')
        return sub_policy_code
    else:
        return "Sub-policy not found"


# Call this function to get the sub_policies of a device type from the local file
@app.route('/get_sub_policies/local/<string:device_type>', methods=['GET'])
def get_sub_policies_local(device_type):
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


# Call this function to get the code of a sub-policy of a device type from the local file
@app.route('/sub_policy_details/local/<string:device_type>/<string:sub_policy_name>', methods=['GET'])
def sub_policy_details_local(device_type, sub_policy_name):
    # Construct the filename from the device_type
    filename = f"policies/{device_type}.py"
    with open(filename, 'r') as f:
        lines = f.readlines()
    try:
        # Find the index of the line that defines the sub-policy
        start_index = next(i for i, line in enumerate(lines) if line.startswith(f'def {sub_policy_name}'))
        # Find the index of the first line after the sub-policy definition that is not indented
        end_index = next(
            i for i, line in enumerate(lines[start_index + 1:], start_index + 1) if not line.startswith(' '))
        # Extract the lines of code that define the sub-policy
        sub_policy_code = ''.join(lines[start_index:end_index])
        return sub_policy_code
    except StopIteration:
        # Handle the case where the sub_policy_name does not exist
        return f"Sub-policy {sub_policy_name} does not exist"


# Call this function to update the policies_dict and actions_dict after a policy has been added
@app.route('/update_policies/<string:device_type>', methods=['PUT'])
def update_policies(device_type):
    module_name = f'policies.{device_type}'
    # If the module has already been imported, reload it to get the updated policy file at runtime
    if module_name in sys.modules:
        module = sys.modules[module_name]
        importlib.reload(module)
    else:
        module = importlib.import_module(module_name)
    # Update the policies_dict and actions_dict
    device_type_policies = getattr(module, 'sub_policies_dict')
    device_type_actions = getattr(module, 'actions_dict')
    policies_dict[device_type] = device_type_policies
    actions_dict[device_type] = device_type_actions
    current_time = datetime.now().strftime('%H:%M:%S')
    current_date = datetime.now().strftime('%Y-%m-%d')

    notification = {
        "message": f"The policies for {device_type} have been updated",
        "time": current_time,
        "date": current_date
    }
    collection_notifications.insert_one(notification)
    new_policies.pop(device_type, None)
    return "Policies updated"


# Used in the functions share_sub_policy and change_sub_policy
def get_sub_policy_data(device_type, sub_policy_name):
    module = importlib.import_module(f'policies.{device_type}')
    if not hasattr(module, 'sub_policies_dict'):
        return "Policy file not found"

    sub_policies_dict = getattr(module, 'sub_policies_dict')
    if sub_policy_name not in [sub_policy.__name__ for priority in sub_policies_dict for sub_policy in
                               sub_policies_dict[priority]]:
        return "Sub-policy not found"
    actions_dict = getattr(module, 'actions_dict')

    # Find priority and actions
    priority = None
    actions = None
    for p in sub_policies_dict:
        if sub_policy_name in [sub_policy.__name__ for sub_policy in sub_policies_dict[p]]:
            priority = p
            break
    if sub_policy_name in actions_dict:
        actions = actions_dict[sub_policy_name]

    # Find sub-policy code and imports
    filename = f'policies/{device_type}.py'
    with open(filename, 'r') as f:
        lines = f.readlines()

    function_start_pattern = re.compile(f'^def {sub_policy_name}\(')
    function_start_index = next((i for i, line in enumerate(lines) if function_start_pattern.match(line)), None)
    if function_start_index is None:
        return jsonify({'error': 'Sub-policy not found'})

    function_end_index = next(
        i for i, line in enumerate(lines[function_start_index + 1:], function_start_index + 1) if
        not line.startswith(' '))
    function_code_lines = lines[function_start_index + 1:function_end_index]
    sub_policy_code = ''.join(line.strip() for line in function_code_lines)

    imports = []
    imported_function_match = re.search(r'from .+ import (\w+)', ''.join(lines))
    if imported_function_match:
        imported_function_name = imported_function_match.group(1)
        import_pattern = re.compile(f'^from .* import .*{imported_function_name}.*$')
        for line in lines:
            if import_pattern.match(line):
                imports.append(line.strip())

    return {
        'priority': priority,
        'actions': actions,
        'sub_policy_name': sub_policy_name,
        'sub_policy_code': sub_policy_code,
        'imports': imports,
        'device_type': device_type
    }


# Define a function to format a list of sub-policies as a string
def format_sub_policies(sub_policies):
    sub_policy_names = []
    for sub_policy in sub_policies:
        if callable(sub_policy):
            sub_policy_names.append(sub_policy.__name__)
        else:
            sub_policy_names.append(sub_policy)
    return '[' + ', '.join(sub_policy_names) + ']'


# Define a function to format a dictionary of sub-policies as a string
def format_sub_policies_dict(sub_policies_dict):
    lines = ['sub_policies_dict = {']
    for key, value in sub_policies_dict.items():
        lines.append(f"    '{key}': {format_sub_policies(value)},")
    lines.append('}')
    return '\n'.join(lines)


# Define a function to format a list of actions as a string
def format_actions(actions):
    lines = []
    for action in actions:
        lines.append(f"        {action},")
    return '\n'.join(lines)


# Define a function to format a dictionary of actions as a string
def format_actions_dict(actions_dict):
    lines = ['actions_dict = {']
    for key, value in actions_dict.items():
        lines.append(f"    '{key}': [")
        lines.append(format_actions(value))
        lines.append('    ],')
    lines.append('}')
    return '\n'.join(lines)


# Used in the functions add_sub_policy and add_sub_policy_from_db
def update_policy_file(device_type, priority, actions, sub_policy_name, sub_policy_code, imports):
    # Retrieve the sub_policies_dict and actions_dict from the module
    module = importlib.import_module(f'policies.{device_type}')
    # Check if the module has the sub_policies_dict and actions_dict attributes or if it is a generic policy file
    if hasattr(module, 'sub_policies_dict'):
        # Retrieve the file content
        sub_policies_dict = getattr(module, 'sub_policies_dict')
        actions_dict = getattr(module, 'actions_dict')
        filename = f'policies/{device_type}.py'
        with open(filename, 'r') as f:
            lines = f.readlines()

        # Check if the sub_policy_name already exists in the sub_policies_dict
        for key in sub_policies_dict:
            for sub_policy in sub_policies_dict[key]:
                # Check if sub_policy is a string or a function
                if isinstance(sub_policy, str):
                    # If it's a string, compare it directly to sub_policy_name
                    if sub_policy_name == sub_policy:
                        return False
                else:
                    # If it's not a string (assumed to be a function), compare its __name__ attribute to sub_policy_name
                    if sub_policy_name == sub_policy.__name__:
                        return False

        # Insert the imports into the list of lines
        for imp in reversed(imports):
            lines.insert(0, imp + '\n\n')

        # Update sub_policies_dict and actions_dict in memory
        sub_policies_dict[priority].append(sub_policy_name)
        actions_dict[sub_policy_name] = actions

        # Find the index of the line that defines the sub_policies_dict
        sub_policies_start_index = next(i for i, line in enumerate(lines) if line.startswith('sub_policies_dict'))

        # Find the index of the line that ends the sub_policies_dict definition
        sub_policies_end_index = next(
            i for i, line in enumerate(lines[sub_policies_start_index:], sub_policies_start_index) if
            line.startswith('}'))

        # Remove the old sub_policies_dict definition from the list of lines
        del lines[sub_policies_start_index:sub_policies_end_index + 1]

        # Insert the new sub_policies_dict definition into the list of lines
        new_sub_policies_lines = format_sub_policies_dict(sub_policies_dict).split('\n')
        for i, line in enumerate(new_sub_policies_lines):
            lines.insert(sub_policies_start_index + i, line + '\n')

        # Find the index of the line that defines the actions_dict
        actions_start_index = next(i for i, line in enumerate(lines) if line.startswith('actions_dict'))

        try:
            # Find the index of the line that ends the actions_dict definition
            actions_end_index = next(
                i for i, line in enumerate(lines[actions_start_index:], actions_start_index) if line.startswith('}'))
        except StopIteration:
            # Handle the error if there is no line break between the {} in the actions_dict
            actions_end_index = actions_start_index
        # Remove the old actions_dict definition from the list of lines
        del lines[actions_start_index:actions_end_index + 1]

        # Insert the new actions_dict definition into the list of lines
        new_actions_lines = format_actions_dict(actions_dict).split('\n')
        for i, line in enumerate(new_actions_lines):
            lines.insert(actions_start_index + i, line + '\n')

        # Insert a blank line to separate the imports from the function definition
        lines.insert(sub_policies_start_index, '\n')

        # Insert the function definition into the list of lines
        lines.insert(sub_policies_start_index + 1, f'def {sub_policy_name}(requesting_device, collection):\n')

        # Insert the sub_policy_code into the list of lines, indented by 4 spaces
        lines.insert(sub_policies_start_index + 2, '    ' + sub_policy_code + '\n\n\n')

        # Write the modified content back to the file
        with open(filename, 'w') as f:
            f.writelines(lines)

        # Update the new_policies dictionary when adding a new policy
        new_policies[device_type] = f'def {sub_policy_name}(requesting_device, collection):\n    {sub_policy_code}\n'

        return True

    else:
        # Retrieve the file content
        filename = f'policies/{device_type}.py'
        with open(filename, 'r') as f:
            lines = f.readlines()

        # Insert the imports into the list of lines
        for imp in reversed(imports):
            lines.insert(0, imp + '\n\n')

        # Set the starting index to the end of the file
        start_index = len(lines)

        # Insert a blank line to separate the imports from the function definition
        lines.insert(start_index, '\n')

        # Insert the function definition into the list of lines
        lines.insert(start_index + 1, f'def {sub_policy_name}(requesting_device, collection):\n')

        # Insert the sub_policy_code into the list of lines, indented by 4 spaces
        lines.insert(start_index + 2, '    ' + sub_policy_code + '\n\n\n')

        # Write the modified content back to the file
        with open(filename, 'w') as f:
            f.writelines(lines)

        # Update the new_policies dictionary when adding a new policy
        new_policies[device_type] = f'def {sub_policy_name}(requesting_device, collection):\n    {sub_policy_code}\n'


# Used in the function failed_policy_actions and evaluate_policies
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


# Used in the function policy_result
def evaluate_policies(sub_policies, possible_actions, requesting_device):
    # Lists to store the failed sub_policies and the actions that need to be executed
    failed_double_check = []
    policy_to_dos = []
    optional_failed = False

    # Execute high priority sub_policies
    for policy in sub_policies['mandatory']:
        result = policy(requesting_device, collection_devices)
        if not result:
            # If a high priority sub_policy fails, the other high priority sub_policies are not executed
            policy_to_dos = []
            return [False, "mandatory", failed_double_check, policy_to_dos]
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
            failed_double_check.append(policy.__name__)
        else:
            # If a double check sub_policy succeeds, the actions of that sub_policy are added to the policy_to_dos
            policy_name = policy.__name__
            add_policy_actions(policy_name, possible_actions, policy_to_dos)

    # Execute low priority sub_policies
    for policy in sub_policies['optional']:
        result = policy(requesting_device, collection_devices)
        if not result:
            optional_failed = True
        else:
            # If a low priority sub_policy succeeds, the actions of that sub_policy are added to the policy_to_dos
            policy_name = policy.__name__
            add_policy_actions(policy_name, possible_actions, policy_to_dos)

    if failed_double_check:
        # If there are failed low priority sub_policies, the policy fails but the double check will be handled in
        #  the message_handler
        return [False, "double_check", failed_double_check, policy_to_dos]

    elif optional_failed:
        # If there are failed low priority sub_policies, but they are not double-check sub_policies
        return [False, "optional", failed_double_check, policy_to_dos]
    else:
        # If all sub_policies succeed, the policy succeeds
        return [True, "N/A", failed_double_check, policy_to_dos]


if __name__ == "__main__":
    app.run(port=8080)
