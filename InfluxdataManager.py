from datetime import datetime
import os

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# You can generate an API token from the "API Tokens Tab" in the UI
token = "v4Hp2CjfX4z9spmgM1vP0W2lqmQdp2QFwY61zZOWpzvvgQ5bZ3gDuzDx9N-O72XkJVlZzQ6Q1JPYJZnou03KUw=="
org = "suravipk@gmail.com"
bucket = "solar"

def SendData(data):
    try:
        with InfluxDBClient(url="https://us-east-1-1.aws.cloud2.influxdata.com", token=token, org=org) as client:
                write_api = client.write_api(write_options=SYNCHRONOUS)
                dataToSend = {}
                dataToSend['measurement'] = "759_2_A_3"
                dataToSend['fields'] = data
                tag = {}
                tag['user'] = 'BMS'
                tag['id'] = 'raspberry'
                dataToSend['tags'] = tag
                write_api.write(bucket, org, dataToSend)
    except Exception as e:
        print(e)



