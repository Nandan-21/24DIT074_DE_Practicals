from faker import Faker
import pandas as pd
import random

fake = Faker()

data = []

for i in range(100):

    data.append({
        "CustomerID": i+1,
        "Name": fake.name(),
        "Email": fake.email(),
        "Age": random.randint(18,65),
        "City": fake.city()
    })

df = pd.DataFrame(data)

df.to_csv("customers.csv",index=False)

print(df.head())