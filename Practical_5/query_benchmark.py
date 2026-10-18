import io
import time
import boto3
from botocore.client import Config
import pandas as pd

MINIO_ENDPOINT = "http://127.0.0.1:9000"
ACCESS_KEY = "minioadmin"
SECRET_KEY = "minioadmin"
BUCKET_NAME = "metrics-lake"

TARGET_YEAR = 2024
TARGET_REGION = "US-WEST"

def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1"
    )

def benchmark_linear_full_scan(s3):
    print("----------------------------------------------------------------")
    print("Method 1: Full-Table Linear File Scan (Unpartitioned)")
    print(f"Goal: Fetch data for year={TARGET_YEAR}, region={TARGET_REGION}")
    print("----------------------------------------------------------------")
    
    start_time = time.perf_counter()
    
    # Linear scan: Must download entire multi-year file and filter in application memory
    obj = s3.get_object(Bucket=BUCKET_NAME, Key="metrics_unpartitioned/all_metrics.csv")
    raw_bytes = obj["Body"].read()
    bytes_downloaded = len(raw_bytes)
    
    df_all = pd.read_csv(io.BytesIO(raw_bytes))
    df_filtered = df_all[(df_all["year"] == TARGET_YEAR) & (df_all["region"] == TARGET_REGION)]
    
    elapsed_time = (time.perf_counter() - start_time) * 1000 # ms
    
    print(f"Total Rows Scanned in Bucket  : {len(df_all)}")
    print(f"Matching Rows Found           : {len(df_filtered)}")
    print(f"Data Transferred Over Network : {bytes_downloaded} bytes ({bytes_downloaded / 1024:.2f} KB)")
    print(f"Linear Scan Execution Time    : {elapsed_time:.3f} ms")
    return elapsed_time, bytes_downloaded, len(df_filtered)

def benchmark_partition_pruned_scan(s3):
    print("\n----------------------------------------------------------------")
    print("Method 2: Partition-Pruned Query (Hive-Style Prefix)")
    print(f"Target Prefix: metrics/year={TARGET_YEAR}/region={TARGET_REGION}/")
    print("----------------------------------------------------------------")
    
    start_time = time.perf_counter()
    
    # Partition pruning: Direct prefix target fetch from S3 namespace
    prefix = f"metrics/year={TARGET_YEAR}/region={TARGET_REGION}/"
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
    
    total_bytes = 0
    frames = []
    if "Contents" in response:
        for item in response["Contents"]:
            obj = s3.get_object(Bucket=BUCKET_NAME, Key=item["Key"])
            content = obj["Body"].read()
            total_bytes += len(content)
            frames.append(pd.read_csv(io.BytesIO(content)))
            
    df_result = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    elapsed_time = (time.perf_counter() - start_time) * 1000 # ms
    
    print(f"Total Rows Read From Prefix   : {len(df_result)}")
    print(f"Data Transferred Over Network : {total_bytes} bytes ({total_bytes / 1024:.2f} KB)")
    print(f"Partition Query Execution Time: {elapsed_time:.3f} ms")
    return elapsed_time, total_bytes, len(df_result)

def main():
    s3 = get_s3_client()
    
    linear_time, linear_bytes, count1 = benchmark_linear_full_scan(s3)
    part_time, part_bytes, count2 = benchmark_partition_pruned_scan(s3)
    
    print("\n================================================================")
    print("PERFORMANCE EVALUATION SUMMARY")
    print("================================================================")
    print(f"Linear Scan Duration   : {linear_time:.3f} ms | Data: {linear_bytes} bytes")
    print(f"Partition Scan Duration: {part_time:.3f} ms | Data: {part_bytes} bytes")
    
    if part_bytes > 0:
        data_reduction = ((linear_bytes - part_bytes) / linear_bytes) * 100
        print(f"Network / IO Reduction : {data_reduction:.1f}% less data scanned")
    if part_time > 0:
        speedup = linear_time / part_time
        print(f"Speedup Ratio          : {speedup:.2f}x faster with Hive partition pruning")
    print("================================================================")

if __name__ == "__main__":
    main()
