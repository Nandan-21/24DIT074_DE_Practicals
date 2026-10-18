import pandas as pd
import json
from datetime import datetime

print("=" * 60)
print("BATCH INGESTION PROCESS")
print("=" * 60)

print("\nBatch ingestion started...")
print("Time:", datetime.now())


customers = pd.read_csv("data/customers.csv")


with open("data/transactions.json", "r") as file:
    transaction_data = json.load(file)

transactions = pd.DataFrame(transaction_data)

print("\nCustomer records loaded:", len(customers))
print("Transaction records loaded:", len(transactions))


customers_clean = customers.drop_duplicates()
transactions_clean = transactions.drop_duplicates()



transactions_clean = transactions_clean[
    transactions_clean["amount"] > 0
]



transactions_clean["timestamp"] = pd.to_datetime(
    transactions_clean["timestamp"],
    errors="coerce"
)



transactions_clean = transactions_clean.dropna(
    subset=["timestamp"]
)


print("\nAfter cleaning:")
print("Customer records:", len(customers_clean))
print("Transaction records:", len(transactions_clean))



customers_clean.to_csv(
    "clean_customers.csv",
    index=False
)

transactions_clean.to_json(
    "clean_transactions.json",
    orient="records",
    indent=4,
    date_format="iso"
)

print("\nCleaned data stored successfully.")

print("\nBatch ingestion completed.")
print("=" * 60)