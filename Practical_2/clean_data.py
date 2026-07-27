import pandas as pd

# Read the CSV file
df = pd.read_csv("customers.csv")

print("Before Cleaning:", len(df), "records")

# Remove rows with missing (null) values
clean_df = df.dropna()

print("After Cleaning:", len(clean_df), "records")

# Save the cleaned data to a new CSV file
clean_df.to_csv("clean_customers.csv", index=False)

print("\nCleaned data has been saved as 'clean_customers.csv'")
print("\nFirst 5 records of cleaned data:")
print(clean_df.head())