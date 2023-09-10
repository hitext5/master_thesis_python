# Policy Server
Operates for both, evaluating the policies and handling the functions of the interface.
Policy server API provides backend for the interface of the project https://github.com/Lordomordo/userinterface and needs to run before starting the interface.
Only the function "policy_result" is used for the message handler from project https://github.com/hitext5/master_thesis_mqtt. 

## To Bootstrap the Project
Install packages: pip install -r requirements.txt 

Setup database:
1. Create account and database on https://cloud.mongodb.com/
2. Create two Users (under "Security" -> "Quickstart"). One with both read and write permission, and one with only read permission.
3. Select "Connect" -> "Drivers" -> Copy the link from bulletpoint 3 into main.py line 12 (atlas_uri_admin) and line 16 (atlas_uri_read). First for all access and second for only read.
       If your IDE can not connect to the database use the Driver Link for Python 3.3 or earlier even with an older version (as in the current version commit 29).
4. Replace line 20 and 21 (rcbms_database_name and policy_database_name) with your database and collection name.


## How it works
If you change the port of the interface also adjust the CORS on line 63 in main.py


If you create a new policy file (python file) add the name to the list on line 33 (device_types) in order to check the policies in this file. Otherwise it will be ignored. 
Make sure to add the dictionaries policies_dict, considerations_dict and actions_dict (even if they are empty). 

To create a new policy in this file, simply create a new function with the parameters (requesting_device, collection) and add it to the policies_dict, then it will be considered for the "policy_result" function.
With the considerations_dict you can specify which "device_id" should be checked. If the function is not in this dictionary, all device ids will be checked. 
The actions_dict lets you trigger functions in the specified "device". To add a function, simply add it under the "to_do" key as a value. 

The devices are handled within the project https://github.com/hitext5/master_thesis_mqtt 
