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
collection = database["devices"]

# Add new policies here
device_types = ['thermostat', 'washer', 'washing_machine', 'window']
policies = {}

# Dynamically import the policies
for device_type in device_types:
    module = importlib.import_module(f'policies.{device_type}')
    device_type_policies = getattr(module, 'sub_policies')
    policies[device_type] = device_type_policies
app = Flask(__name__)


@app.route('/check_policies/<string:device_type>', methods=['POST'])
def policy_result(device_type):
    data = request.get_json()
    policy_of_requesting_device = policies.get(device_type)
    if policy_of_requesting_device:
        result = evaluate_policies(policy_of_requesting_device, data)
        return jsonify({"result": result[0], "priority": result[1], "failed_sub_policies": result[2]})
    else:
        # There is no policy for this device type
        return jsonify({"result": True})
        # return 'Invalid policy name', 400


@app.route('/add_policy', methods=['POST'])
def add_policy():
    data = request.get_json()
    priority = data['priority']
    sub_policy_name = data['sub_policy_name']
    sub_policy_code = data['sub_policy_code']
    device_type = data['device_type']

    # Dynamically import the specified eval method
    module = importlib.import_module(f'policies.{device_type}')
    sub_policies = getattr(module, 'sub_policies')

    # TODO Add the sub_policy_name directly into the policy
    # Save the method code to a file
    with open('methods.txt', 'a') as f:
        f.write(sub_policy_code + '\n')

    # TODO Maybe introduce an if else statement to check if it is a sub policy for a
    #  single device type or multiple device types like electronic device applies to washing machine and washer
    # Add the sub_policy_name to the list of sub_policies for the specified priority
    # In order for getattr to work, the sub_policy_name must be the same as the method name, without def,
    #  and the method must already be defined in the policy file
    sub_policy = getattr(module, sub_policy_name)
    if sub_policy in sub_policies[priority]:
        # TODO Show notification in user-interface
        return 'Double entry', 400
    else:
        sub_policies[priority].append(sub_policy)

    return 'Success'


# TODO Add a method to delete a policy
# TODO Add a method to update a policy

@app.route('/get_sub_policies/<string:device_type>', methods=['POST'])
def get_sub_policies(device_type):
    # TODO Currently only displays the name of the sub_policy, not the code
    module = importlib.import_module(f'policies.{device_type}')
    specific_policies = []
    general_policies = []
    for _, sub_policies in policies[device_type].items():
        for sub_policy in sub_policies:
            if sub_policy.__module__ == module.__name__:
                specific_policies.append(sub_policy.__name__)
            else:
                general_policies.append(sub_policy.__name__)

    return jsonify({
        'specific_policies': specific_policies,
        'general_policies': general_policies
    })


def evaluate_policies(sub_policies, requesting_device):
    failed_sub_policies = []

    # Execute high priority sub_policies
    for policy in sub_policies['mandatory']:
        if not policy(requesting_device, collection):
            return [False, "mandatory", failed_sub_policies]

    # Execute low priority sub_policies
    for policy in sub_policies['double_check']:
        if not policy(requesting_device, collection):
            failed_sub_policies.append(policy.__name__)

    if failed_sub_policies:
        return [False, "double_check", failed_sub_policies]

    return [True, "N/A", failed_sub_policies]


if __name__ == "__main__":
    app.run(port=8080)
