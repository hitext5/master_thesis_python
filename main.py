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
    sub_policy = data['sub_policy']
    policy_code = data['policy_code']
    device_type = data['device_type']

    # Dynamically define the method
    # exec(policy_code)

    # Get the method from the global scope
    # method = globals()[sub_policy]

    # Dynamically import the specified eval method
    module = importlib.import_module(f'policies.{device_type}')
    device_type_policy = getattr(module, f'eval_{device_type}_policies')

    # Add the sub_policy to the list of sub_policies for the specified priority
    device_type_policy.sub_policies[priority].append(sub_policy)

    # TODO Execute the file in the policy or add the sub_policy directly into the policy
    # Save the method code to a file
    with open('methods.txt', 'a') as f:
        f.write(policy_code + '\n')

    return 'Success'


if __name__ == "__main__":
    app.run(port=8080)
