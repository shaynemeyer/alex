"""
Clean up S3 Vectors database by removing all test data.
This script directly accesses S3 Vectors without going through API Gateway.
Also cleans the Supabase research_documents table if credentials are present.
"""

import os
import json
import boto3
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client

# Load environment variables from project root
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path, override=True)

# Get configuration
VECTOR_BUCKET = os.getenv('VECTOR_BUCKET')
INDEX_NAME = 'financial-research'
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

if not VECTOR_BUCKET:
    print("Error: VECTOR_BUCKET not found in .env")
    exit(1)

# Initialize S3 Vectors client
s3_vectors = boto3.client('s3vectors')

def delete_all_vectors():
    """Delete all vectors from the index."""
    print("Cleaning S3 Vectors database...")
    print(f"Bucket: {VECTOR_BUCKET}")
    print(f"Index: {INDEX_NAME}")
    print()
    
    deleted_count = 0
    
    try:
        # S3 Vectors doesn't have a list operation, so we need to search broadly
        print("Searching for vectors to delete...")
        
        # Get a real embedding for a generic search term
        sagemaker_runtime = boto3.client('sagemaker-runtime')
        SAGEMAKER_ENDPOINT = os.getenv('SAGEMAKER_ENDPOINT', 'alex-embedding-endpoint')
        
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=SAGEMAKER_ENDPOINT,
            ContentType='application/json',
            Body='{"inputs": "document"}'
        )
        
        result = json.loads(response['Body'].read().decode())
        # Extract from nested array [[[embedding]]]
        dummy_vector = result[0][0]
        
        # S3 Vectors limits topK to 30, so we need to loop
        all_vectors = []
        batch_size = 30
        
        while True:
            response = s3_vectors.query_vectors(
                vectorBucketName=VECTOR_BUCKET,
                indexName=INDEX_NAME,
                queryVector={"float32": dummy_vector},
                topK=batch_size,
                returnMetadata=True
            )
            
            vectors = response.get('vectors', [])
            if not vectors:
                break
                
            all_vectors.extend(vectors)
            
            # Delete this batch before getting more
            print(f"  Found batch of {len(vectors)} vectors...")
            for vector in vectors:
                try:
                    s3_vectors.delete_vectors(
                        vectorBucketName=VECTOR_BUCKET,
                        indexName=INDEX_NAME,
                        keys=[vector['key']]
                    )
                    deleted_count += 1
                except Exception as e:
                    print(f"  Error deleting {vector['key']}: {e}")
            
            # If we got less than batch_size, we're done
            if len(vectors) < batch_size:
                break
        
        if deleted_count > 0:
            print(f"\n✅ Successfully deleted {deleted_count} vectors")
        else:
            print("✅ No vectors found - database is already empty")
            
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        if deleted_count > 0:
            print(f"   (Partially successful - deleted {deleted_count} vectors)")

def delete_all_supabase_records():
    """Delete all rows from research_documents in Supabase."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("Skipping Supabase cleanup (SUPABASE_URL / SUPABASE_SERVICE_KEY not set)")
        return

    print("Cleaning Supabase research_documents table...")
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        # PostgREST requires a filter for DELETE; match all rows via epoch timestamp
        result = supabase.table('research_documents').delete().gte('created_at', '1970-01-01').execute()
        deleted = len(result.data) if result.data else 0
        print(f"Deleted {deleted} row(s) from research_documents")
    except Exception as e:
        print(f"Error during Supabase cleanup: {e}")


def main():
    """Clean up S3 Vectors and Supabase research data."""
    print("=" * 60)
    print("Research Data Cleanup")
    print("=" * 60)
    print()

    # Confirm before deleting
    response = input("This will DELETE ALL vectors and Supabase research records. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Cleanup cancelled.")
        return

    print()
    delete_all_vectors()
    print()
    delete_all_supabase_records()

    print("\nTip: Run test_api.py to add new test data")

if __name__ == "__main__":
    main()