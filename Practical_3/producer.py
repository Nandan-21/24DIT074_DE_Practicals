from kafka import KafkaProducer
import json
import time


producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda x: json.dumps(x).encode("utf-8")
)

topic = "student_latency"


students = [
    {"id": 101, "name": "Maharsh", "dept": "IT"},
    {"id": 102, "name": "Dhairya", "dept": "CE"},
    {"id": 103, "name": "Milan", "dept": "CSE"}
]


print("Producer started")


for student in students:

    # Add sending timestamp
    student["timestamp"] = time.time()

    producer.send(topic, student)

    print("Sent:", student)

    time.sleep(1)


producer.flush()
producer.close()

print("Producer finished")
