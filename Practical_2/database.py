import sqlite3
import pandas as pd

conn = sqlite3.connect("customers.db")

df = pd.read_csv("customers.csv")

df.to_sql("Customers",conn,if_exists="replace",index=False)

print("Database Created")

conn.close()