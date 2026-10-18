import pandas as pd
import json

print("=" * 60)
print("DATA ENGINEERING PRACTICAL")
print("=" * 60)

print("\n1. LOADING CUSTOMER DATA")

customers = pd.read_csv("data/customers.csv")

print(customers)

print("\n2. CUSTOMER DATA PROFILING")

print("\nShape:")
print(customers.shape)

print("\nColumns:")
print(customers.columns.tolist())

print("\nData Types:")
print(customers.dtypes)

print("\nMissing Values:")
print(customers.isnull().sum())

print("\nDuplicate Records:")
print(customers.duplicated().sum())

print("\n3. LOADING TRANSACTION DATA")

with open("data/transactions.json", "r") as file:
    transaction_data = json.load(file)

transactions = pd.DataFrame(transaction_data)

print(transactions)

print("\n4. TRANSACTION DATA PROFILING")

print("\nShape:")
print(transactions.shape)

print("\nColumns:")
print(transactions.columns.tolist())

print("\nData Types:")
print(transactions.dtypes)

print("\nMissing Values:")
print(transactions.isnull().sum())

print("\nDuplicate Records:")
print(transactions.duplicated().sum())

print("\n5. INVALID TRANSACTION AMOUNTS")

invalid_amounts = transactions[
    transactions["amount"] <= 0
]

print(invalid_amounts)

print("\n6. DATE FORMAT CHECK")

transactions["parsed_timestamp"] = pd.to_datetime(
    transactions["timestamp"],
    errors="coerce"
)

invalid_dates = transactions[
    transactions["parsed_timestamp"].isnull()
]

print("Invalid dates:")
print(invalid_dates)

print("\n" + "=" * 60)
print("PROFILING COMPLETED")
print("=" * 60)