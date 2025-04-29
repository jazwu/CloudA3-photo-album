import json
import boto3
import urllib3
import base64

# Initialize AWS clients
lex = boto3.client('lexv2-runtime', region_name='us-east-1')
BOT_ID = "VJZM95V9PJ"
BOT_ALIAS_ID = "TSTALIASID"

# Initialize Elasticsearch client
http = urllib3.PoolManager()
USERNAME = "username"
PASSWORD = "Usn#2025"
auth_header = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()

host = 'https://search-photos-gsd44g2m5zcpgetsvoafgiewse.aos.us-east-2.on.aws'
index = 'photos'
url = host + '/' + index + '/_search'

def expand_keywords_with_singular_and_plural(keywords):
    """
    Expands keywords to include both singular and plural forms
    
    Args:
        keywords (list): Original keywords from user query
        
    Returns:
        list: Expanded list with both singular and plural forms
    """
    expanded_keywords = []
    
    for keyword in keywords:
        expanded_keywords.append(keyword)
        
        # Convert plural to singular
        if keyword.endswith('s'):
            # Simple plural: cats -> cat
            expanded_keywords.append(keyword[:-1])
            
            # Words ending in 'ies': butterflies -> butterfly
            if keyword.endswith('ies'):
                expanded_keywords.append(keyword[:-3] + 'y')
            
            # Words ending in 'es': beaches -> beach
            elif keyword.endswith('es'):
                expanded_keywords.append(keyword[:-2])
        
        # Convert singular to plural
        else:
            # Simple singular: cat -> cats
            expanded_keywords.append(keyword + 's')
            
            # Words ending in 'y': butterfly -> butterflies
            if keyword.endswith('y') and not is_vowel(keyword[-2]):
                expanded_keywords.append(keyword[:-1] + 'ies')
            
            # Words ending in specific consonants: beach -> beaches
            elif keyword.endswith(('sh', 'ch', 's', 'x', 'z')):
                expanded_keywords.append(keyword + 'es')
            
            # Words ending in 'f' or 'fe': wolf -> wolves, knife -> knives
            elif keyword.endswith('f'):
                expanded_keywords.append(keyword[:-1] + 'ves')
            elif keyword.endswith('fe'):
                expanded_keywords.append(keyword[:-2] + 'ves')
    
    return list(set(expanded_keywords))


def lambda_handler(event, context):

    try:
        # Step i: Get the query from the event
        query = event['queryStringParameters'].get('q', '')
        
        if not query:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'message': 'Missing query parameter',
                    'results': []
                })
            }
        print("Query:", query)
        
        # Disambiguate the query using Amazon Lex bot
        lex_response = lex.recognize_text(
            botId=BOT_ID,
            botAliasId=BOT_ALIAS_ID,
            localeId='en_US',
            sessionId='search-photos-session',
            text=query
        )

        print("Lex response:", lex_response)
        
        # Step ii: Extract keywords from Lex response
        keywords = []
        
        # Check if we have slots in the Lex response
        if 'slots' in lex_response.get('interpretations', [{}])[0].get('intent', {}):
            slots = lex_response['interpretations'][0]['intent']['slots']
            
            # Extract all non-null slots as keywords
            for slot_name, slot_value in slots.items():
                if slot_value and 'value' in slot_value:
                    # Add the keyword to our list
                    keyword = slot_value['value']['interpretedValue'].lower()
                    keywords.append(keyword)
        
        # If no keywords were found, return empty results
        if not keywords:
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'message': 'No valid keywords found in query',
                    'results': []
                })
            }
        
        # Expand keywords with singular and plural forms
        keywords = expand_keywords_with_singular_and_plural(keywords)

        print("Keywords:", keywords)
        
        # Build Elasticsearch query using keywords
        es_query = {
            'query': {
                'bool': {
                    'should': [
                        {'match': {'labels': keyword}} for keyword in keywords
                    ],
                    'minimum_should_match': 1
                }
            }
        }
        
        # Execute search against the photos index
        response = http.request(
            'GET', url, headers={'Authorization': f'Basic {auth_header}', "Content-Type": "application/json",},
            body=json.dumps(es_query).encode('utf-8')
        )
        response_text = response.data.decode("utf-8").strip()

        if not response_text:  # If response is empty
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'message': 'No results found',
                    'results': []
                })
            }
        
        es_response = json.loads(response_text)

        print("Elasticsearch response:", es_response)
        
        # Transform Elasticsearch results into API response format
        results = []
        for hit in es_response['hits']['hits']:
            source = hit['_source']
            
            # Construct S3 URL for the image
            s3_url = f"https://{source['bucket']}.s3.amazonaws.com/{source['objectKey']}"
            
            # Add the result to our response
            result = {
                'url': s3_url,
                'labels': source['labels']
            }
            results.append(result)
        
        # Return the search results
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'results': results
            })
        }
        
    except Exception as e:
        print(f'Error searching photos: {str(e)}')
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': f'Error searching photos: {str(e)}',
                'results': []
            })
        }