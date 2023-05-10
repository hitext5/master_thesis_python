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
policies = ['thermostat', 'washer', 'washing_machine', 'window']
policy_methods = {}

# Dynamically import the policies
for policy in policies:
    module = importlib.import_module(f'policies.{policy}')
    method = getattr(module, f'eval_{policy}_policies')
    policy_methods[policy] = method

app = Flask(__name__)


@app.route('/policies/<string:device_type>', methods=['POST'])
def policy_result(device_type):
    data = request.get_json()
    # Lookup table for policies n(1)
    method = policy_methods.get(device_type)
    if method:
        result = method(data, collection)
        return jsonify({"result": result})
    else:
        # There is no policy for this device type
        return jsonify({"result": True})
        # return 'Invalid policy name', 400


if __name__ == "__main__":
    app.run(port=8080)
