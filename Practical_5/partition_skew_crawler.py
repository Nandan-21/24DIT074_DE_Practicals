import re
import boto3
from botocore.client import Config
import pandas as pd

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

def crawl_partition_skew():
    print("================================================================")
    print("OBJECT STORAGE PARTITION METADATA & SKEW CRAWLER")
    print(f"Target Bucket: {BUCKET_NAME} | Prefix: metrics/")
    print("================================================================")
    
    s3 = get_s3_client()
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix="metrics/")
    
    partition_records = []
    
    # Hive partition pattern: metrics/year=XXXX/region=YYYY/...
    pattern = re.compile(r"metrics/year=([^/]+)/region=([^/]+)/")
    
    for page in pages:
        if "Contents" in page:
            for obj in page["Contents"]:
                key = obj["Key"]
                size_bytes = obj["Size"]
                last_modified = obj["LastModified"]
                
                match = pattern.search(key)
                if match:
                    year, region = match.group(1), match.group(2)
                    partition_name = f"year={year}/region={region}"
                    partition_records.append({
                        "partition": partition_name,
                        "year": year,
                        "region": region,
                        "object_key": key,
                        "size_bytes": size_bytes,
                        "last_modified": last_modified
                    })
    
    if not partition_records:
        print("No partitioned objects discovered under prefix 'metrics/'.")
        return
        
    df_meta = pd.DataFrame(partition_records)
    
    # Aggregate partition balance metrics
    summary = df_meta.groupby("partition").agg(
        object_count=("object_key", "count"),
        total_bytes=("size_bytes", "sum")
    ).reset_index()
    
    total_lake_bytes = summary["total_bytes"].sum()
    summary["size_kb"] = (summary["total_bytes"] / 1024).round(2)
    summary["storage_share_pct"] = ((summary["total_bytes"] / total_lake_bytes) * 100).round(2)
    
    # Skew metrics
    mean_bytes = summary["total_bytes"].mean()
    max_bytes = summary["total_bytes"].max()
    min_bytes = summary["total_bytes"].min()
    
    summary["skew_deviation_bytes"] = summary["total_bytes"] - mean_bytes
    summary["skew_ratio_to_mean"] = (summary["total_bytes"] / mean_bytes).round(3)
    
    print("\n--- ACTIVE PARTITION DISTRIBUTION TABLE ---")
    print(summary[["partition", "object_count", "size_kb", "storage_share_pct", "skew_ratio_to_mean"]].to_string(index=False))
    
    print("\n--- GLOBAL PARTITION SKEW EVALUATION ---")
    print(f"Total Partitions Scanned       : {len(summary)}")
    print(f"Total Storage In Lake          : {total_lake_bytes} bytes ({total_lake_bytes / 1024:.2f} KB)")
    print(f"Mean Partition Size            : {mean_bytes:.2f} bytes")
    print(f"Min Partition Size             : {min_bytes} bytes")
    print(f"Max Partition Size             : {max_bytes} bytes")
    skew_factor = (max_bytes / min_bytes) if min_bytes > 0 else 1.0
    print(f"Partition Skew Factor (Max/Min): {skew_factor:.3f}")
    if skew_factor <= 1.25:
        print("Status: IDEAL BALANCE - Storage is evenly distributed across partitions.")
    else:
        print("Status: PARTITION SKEW DETECTED - Certain partitions hold disproportionate data volume.")
    print("================================================================")

if __name__ == "__main__":
    crawl_partition_skew()
