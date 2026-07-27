import pandas as pd

# Read the CSV file
df = pd.read_csv("customers.csv")

# Find duplicate rows
duplicates = df[df.duplicated()]

# Display duplicate records
if duplicates.empty:
    print("No duplicate records found.")
else:
    print("Duplicate Records:")
    print(duplicates)

# Count duplicate records
print("\nTotal Duplicate Records:", duplicates.shape[0])