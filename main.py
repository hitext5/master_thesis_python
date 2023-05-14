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
    device_type_policy = getattr(module, f'eval_{device_type}_policies')
    policies[device_type] = device_type_policy

app = Flask(__name__)


@app.route('/policies/<string:device_type>', methods=['POST'])
def policy_result(device_type):
    data = request.get_json()
    # Lookup table for policies n(1)
    policy_of_requesting_device = policies.get(device_type)
    if policy_of_requesting_device:
        result = policy_of_requesting_device(data, collection)
        return jsonify({"result": result[0], "priority": result[1]})
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

    # Dynamically define the method
    # exec(sub_policy_code)

    # Get the method from the global scope
    # method = globals()[sub_policy_name]

    # Dynamically import the specified eval method
    module = importlib.import_module(f'policies.{device_type}')
    device_type_policy = getattr(module, f'eval_{device_type}_policies')

    # TODO Add the sub_policy_name directly into the policy
    # Save the method code to a file
    with open('methods.txt', 'a') as f:
        f.write(sub_policy_code + '\n')

    # TODO Maybe introduce an if else statement to check if it is a sub policy for a
    #  single device type or multiple device types like electronic device applies to washing machine and washer
    # Add the sub_policy_name to the list of sub_policies for the specified priority
    # TODO In order for getattr to work, the sub_policy_name must be the same as the method name, without def,
    #  and the method must already be defined in the policy file
    sub_policy = getattr(module, sub_policy_name)
    if sub_policy in device_type_policy.sub_policies[priority]:
        # Double entry
        # Send notification over API
        pass
    else:
        device_type_policy.sub_policies[priority].append(sub_policy)

    return 'Success'


# TODO Add a method to delete a policy
# TODO Add a method to update a policy


if __name__ == "__main__":
    app.run(port=8080)
