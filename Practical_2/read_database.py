import sqlite3
import pandas as pd

# Connect to the database
conn = sqlite3.connect("customers.db")

# Read data from the Customers table
df = pd.read_sql("SELECT * FROM Customers", conn)

# Display the data
print(df)

# Close the connection
conn.close()