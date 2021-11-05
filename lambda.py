import json
import boto3
import base64
import urllib3
import urllib.parse
from botocore.exceptions import ClientError
import time

s3 = boto3.client('s3')
bucket = "leo-ranz"
timestamp_key = 'timestamp.json'
ranMeters_key = 'ran_meters.json'

meter = 5000000

strava_activitie_url = "https://www.strava.com/api/v3//clubs/913376/activities"
strava_refresh_url = "https://www.strava.com/oauth/token"

def lambda_handler(event, context):
    
    timestamp_request = s3.get_object(
        Bucket = bucket, 
        Key = timestamp_key
        )
        
    last_timestamp = json.loads(timestamp_request['Body'].read())
    current_timestamp = int(time.time())
    past_time = current_timestamp - last_timestamp
    # 20 Minuten cache 
    if past_time < 1200:
        ran_meters_request = s3.get_object(
            Bucket = bucket,
            Key = ranMeters_key
            )
        ran_meters = json.loads(ran_meters_request['Body'].read())
        return {
            'statusCode': 200,
            'body' : json.dumps({
                'ranMeters' : ran_meters['ranMeters']
            })
            }
    
    # SecretsManager
    secretValues = json.loads(get_secret())
    http = urllib3.PoolManager()
    token = http.request('post',
                     strava_refresh_url,
                     fields={
                         "client_id" : secretValues['client_id'],
                         "client_secret": secretValues['client_secret'],
                         "grant_type": "refresh_token",
                         "refresh_token": secretValues['refresh_token']
                     })
                     
    credentials = json.loads(token.data.decode('utf-8'))
    access_token = credentials.get('access_token')
    
    page = 1
    per_page = 200
    has_result = True
    runs = []
    distance = 0
    
    while has_result:
        has_result = False
        activities = http.request(
            'get',
            strava_activitie_url,
            fields={
                'page': page,
                'per_page': per_page
            },
            headers={
                'Authorization': 'Bearer ' + access_token
            }
        )
        current_page_data = json.loads(activities.data.decode('utf-8'))
        runs = current_page_data
        for details in runs:
            distance = distance + details['distance']
                
        if len(runs):
            has_result = False
        
    s3.put_object(
        Body = json.dumps({
            "ranMeters" : 5000000 - distance
        }),
        Bucket = bucket, 
        Key = ranMeters_key
        )
    s3.put_object(
        Body = json.dumps(int(time.time())),
        Bucket = bucket,
        Key = timestamp_key
        )
        
    test = {
        'ranMeters' : 5000000 - distance
    }
    return {
        'statusCode': 200,
        'body': json.dumps(test),
        'test': distance
    }
