import json
import boto3
import urllib3
import base64

http = urllib3.PoolManager()
USERNAME = "username"
PASSWORD = "Usn#2025"
auth_header = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()

host = 'https://search-photos-gsd44g2m5zcpgetsvoafgiewse.aos.us-east-2.on.aws'
index = 'photos'
url = host + '/' + index + '/_doc'

# Initialize AWS clients
rekognition = boto3.client('rekognition', region_name='us-east-2')
s3 = boto3.client('s3', region_name='us-east-2')

def lambda_handler(event, context):
    try:
        responses = []
        
        # Process each record from the S3 event
        for record in event['Records']:
            # Extract bucket and key information from the S3 PUT event (E1)
            bucket = record['s3']['bucket']['name']
            object_key = record['s3']['object']['key'].replace('+', ' ')
            
            # Step i: Retrieve S3 metadata using head_object method
            s3_metadata = s3.head_object(
                Bucket=bucket,
                Key=object_key
            )
            print(f"Object exists: s3://{bucket}/{object_key}")
            
            # Create the labels array (A1)
            labels_array = []
            
            # Check if custom labels exist in the x-amz-meta-customLabels metadata field
            if 'Metadata' in s3_metadata and 'customlabels' in s3_metadata['Metadata']:
                # Add the custom labels to the labels array
                custom_labels = [label.strip().lower() for label in s3_metadata['Metadata']['customlabels'].split(',')]
                labels_array = custom_labels

            # Step ii: Use Rekognition to detect labels in the image
            rekognition_response = rekognition.detect_labels(
                Image={
                    'S3Object': {
                        'Bucket': bucket,
                        'Name': object_key
                    }
                },
                MaxLabels=100,
                MinConfidence=70
            )
            
            detected_labels = [label['Name'].lower() for label in rekognition_response['Labels']]
            
            # Step iii: Append Rekognition detected labels to the labels array
            labels_array = list(set(labels_array + detected_labels))  # Remove duplicates
            
            # Create timestamp for ElasticSearch
            created_timestamp = s3_metadata.get('LastModified', '').isoformat() if 'LastModified' in s3_metadata else None
            if not created_timestamp:
                from datetime import datetime
                created_timestamp = datetime.now().isoformat()
            
            # Create JSON object for ElasticSearch
            es_document = {
                'objectKey': object_key,
                'bucket': bucket,
                'createdTimestamp': created_timestamp,
                'labels': labels_array
            }
            
            # Store the document in ElasticSearch index "photos"
            r = http.request('POST', url, body=json.dumps(es_document).encode("utf-8"), headers={'Content-Type': 'application/json', 'Authorization': f'Basic {auth_header}'})
            r_text = r.data.decode("utf-8").strip()
            r_json = json.loads(r_text)

            # Create the response and add some extra content to support CORS
            response = {
                'statusCode': 200,
                'headers': {
                    "Access-Control-Allow-Origin": '*'
                },
                'body': json.dumps({
                    'message': 'Image processed successfully',
                    'id': r_json['_id'],
                    'labels': labels_array
                })
            }
            
            responses.append(response)
        
        return responses
        
    except Exception as e:
        print(f'Error processing image: {str(e)}')
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error processing image',
                'error': str(e)
            })
        }