import duckdb
import time

start = time.time()

con = duckdb.connect("retail.duckdb")

con.execute("DROP TABLE IF EXISTS staging_sales")

con.execute("""
    CREATE TABLE staging_sales AS
    SELECT * FROM read_csv_auto('sales.csv')
""")

print("Raw data loaded into staging table.")

con.execute("DROP TABLE IF EXISTS elt_sales")

con.execute("""
    CREATE TABLE elt_sales AS
    SELECT
        transaction_id,
        TRIM(customer_name) AS customer_name,
        CAST(amount AS DOUBLE) AS amount,
        CASE
            WHEN TRIM(store_code) = 'OLD-03' THEN 'GJ-03'
            WHEN TRIM(store_code) = 'OLD-04' THEN 'GJ-04'
            ELSE TRIM(store_code)
        END AS store_code
    FROM staging_sales
""")

print("\nTransformed ELT data:")
print(con.execute("SELECT * FROM elt_sales").fetchdf())

con.close()

end = time.time()

print("\nELT completed successfully.")
print("ELT Time:", round(end - start, 4), "seconds")