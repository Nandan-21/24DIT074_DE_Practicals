import pandas as pd

df=pd.read_csv("customers.csv")

print(df.info())

print()

print(df.describe())

print()

print(df.isnull().sum())