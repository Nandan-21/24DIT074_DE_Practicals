import io
import boto3
from botocore.client import Config
import pandas as pd

# MinIO S3 Configuration
MINIO_ENDPOINT = "http://127.0.0.1:9000"
ACCESS_KEY = "minioadmin"
SECRET_KEY = "minioadmin"
BUCKET_NAME = "metrics-lake"

def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1"
    )

def main():
    s3 = get_s3_client()
    
    # 1. Ensure bucket exists
    try:
        s3.create_bucket(Bucket=BUCKET_NAME)
        print(f"Bucket '{BUCKET_NAME}' created successfully.")
    except s3.exceptions.BucketAlreadyOwnedByYou:
        print(f"Bucket '{BUCKET_NAME}' already exists and is owned by you.")
    except Exception as e:
        print(f"Bucket check note: {e}")

    # 2. Read generated metrics dataset
    df = pd.read_csv("application_metrics.csv")
    print(f"Loaded {len(df)} records from application_metrics.csv")

    # 3. Upload full unpartitioned file (for baseline linear full-scan benchmark)
    unpartitioned_key = "metrics_unpartitioned/all_metrics.csv"
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    s3.put_object(Bucket=BUCKET_NAME, Key=unpartitioned_key, Body=csv_buffer.getvalue())
    print(f"Uploaded unpartitioned dataset to: s3://{BUCKET_NAME}/{unpartitioned_key}")

    # 4. Partition and upload using Hive-style prefix keys: metrics/year=YYYY/region=REG/data.csv
    print("\nUploading partitioned data using structured Hive-style keys...")
    grouped = df.groupby(["year", "region"])
    
    upload_count = 0
    for (year, region), group_df in grouped:
        hive_key = f"metrics/year={year}/region={region}/data.csv"
        part_buffer = io.StringIO()
        group_df.to_csv(part_buffer, index=False)
        
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=hive_key,
            Body=part_buffer.getvalue(),
            ContentType="text/csv"
        )
        print(f" -> Uploaded partition: {hive_key} ({len(group_df)} rows)")
        upload_count += 1

    print(f"\nSuccessfully uploaded {upload_count} Hive-style partitions to MinIO S3.")

if __name__ == "__main__":
    main()
