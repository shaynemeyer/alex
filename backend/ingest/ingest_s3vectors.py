"""
Lambda function for ingesting text into S3 Vectors with embeddings.
"""

import json
import os
import boto3
import datetime
import uuid
from supabase import create_client

# Environment variables
VECTOR_BUCKET = os.environ.get('VECTOR_BUCKET', 'alex-vectors')
SAGEMAKER_ENDPOINT = os.environ.get('SAGEMAKER_ENDPOINT')
INDEX_NAME = os.environ.get('INDEX_NAME', 'financial-research')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')

# Initialize AWS clients
sagemaker_runtime = boto3.client('sagemaker-runtime')
s3_vectors = boto3.client('s3vectors')


def parse_bullet_points(text: str) -> list:
    """Extract bullet-point lines from research text."""
    bullets = []
    for line in text.strip().splitlines():
        s = line.strip()
        if not s:
            continue
        if s[0] in ('-', '•', '*') or (len(s) > 2 and s[0].isdigit() and s[1] in '.)'):
            bullets.append(s.lstrip('-•* 0123456789.)').strip())
    return bullets


def get_embedding(text):
    """Get embedding vector from SageMaker endpoint."""
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT,
        ContentType='application/json',
        Body=json.dumps({'inputs': text})
    )
    
    result = json.loads(response['Body'].read().decode())
    # HuggingFace returns nested array [[[embedding]]], extract the actual embedding
    if isinstance(result, list) and len(result) > 0:
        if isinstance(result[0], list) and len(result[0]) > 0:
            if isinstance(result[0][0], list):
                return result[0][0]  # Extract from [[[embedding]]]
            return result[0]  # Extract from [[embedding]]
    return result  # Return as-is if not nested


def lambda_handler(event, context):
    """
    Main Lambda handler.
    Expects JSON body with:
    {
        "text": "Text to ingest",
        "metadata": {
            "source": "optional source",
            "category": "optional category"
        }
    }
    """
    try:
        # Parse the request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        text = body.get('text')
        metadata = body.get('metadata', {})
        
        if not text:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required field: text'})
            }
        
        # Get embedding from SageMaker
        print(f"Getting embedding for text: {text[:100]}...")
        embedding = get_embedding(text)
        
        # Generate unique ID for the vector
        vector_id = str(uuid.uuid4())
        
        # Store in S3 Vectors
        print(f"Storing vector in bucket: {VECTOR_BUCKET}, index: {INDEX_NAME}")
        s3_vectors.put_vectors(
            vectorBucketName=VECTOR_BUCKET,
            indexName=INDEX_NAME,
            vectors=[{
                "key": vector_id,
                "data": {"float32": embedding},
                "metadata": {
                    "text": text,
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    **metadata  # Include any additional metadata
                }
            }]
        )
        
        # Write structured record to Supabase
        if SUPABASE_URL and SUPABASE_SERVICE_KEY:
            supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
            supabase.table('research_documents').insert({
                'vector_id': vector_id,
                'topic': metadata.get('topic'),
                'full_text': text,
                'bullet_points': parse_bullet_points(text),
                'researched_at': metadata.get('timestamp'),
            }).execute()
            print(f"Stored structured record in Supabase for vector_id: {vector_id}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Document indexed successfully',
                'document_id': vector_id
            })
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }