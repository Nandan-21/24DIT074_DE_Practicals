import json
import time
from datetime import datetime

print("=" * 60)
print("STREAMING INGESTION PROCESS")
print("=" * 60)

with open("data/transactions.json", "r") as file:
    events = json.load(file)

print("\nStreaming started...")
print("Waiting for incoming events...\n")


for event in events:

    print("Incoming event received:")
    print(event)

    if event["amount"] <= 0:
        print("WARNING: Invalid transaction amount")
        print("Event rejected.\n")
        continue

    print("Event processed successfully.")
    print("Transaction ID:", event["transaction_id"])
    print("Customer ID:", event["customer_id"])
    print("Amount:", event["amount"])
    print("Processing time:", datetime.now())

    print("-" * 50)

   
    time.sleep(2)


print("\nStreaming ingestion completed.")
print("=" * 60)
