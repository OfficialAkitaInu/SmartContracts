import json

def load_test_config(file_path='./test/testConfig.json'):
    fp = open(file_path)
    return json.load(fp)
