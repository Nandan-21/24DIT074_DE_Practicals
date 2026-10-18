import pandas as pd
import duckdb
import time

start = time.time()

df = pd.read_csv('sales.csv')
print('Raw data:')
print(df)

df['customer_name'] = df['customer_name'].str.strip()
df['amount'] = pd.to_numeric(df['amount'])

df["store_code"] = df["store_code"].str.strip()
df["store_code"] = df["store_code"].replace({
    "OLD-03": "GJ-03",
    "OLD-04": "GJ-04"
})

print("\nTransformed Data:")
print(df)

con = duckdb.connect('retail.duckdb')
con.execute("DROP TABLE IF EXISTS etl_sales")
con.execute("""
    CREATE TABLE etl_sales AS
    SELECT * from df
""")

con.close()

end = time.time()
print("\nETL completed successfully.")
print("ETL Time:", round(end - start, 4), "seconds")