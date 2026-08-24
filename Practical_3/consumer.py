# CREATE NEW TOPIC NAMED: student_latency

from kafka import KafkaConsumer
import json
import time


consumer = KafkaConsumer(
    "student_latency",
    bootstrap_servers="localhost:9092",
    auto_offset_reset="earliest",
    value_deserializer=lambda x: json.loads(x.decode("utf-8"))
)


print("Consumer started")
print("Waiting for messages...")


count = 0
start_time = time.time()

total_latency = 0


for message in consumer:

    data = message.value

    receive_time = time.time()

    # Calculate latency in milliseconds
    latency = (receive_time - data["timestamp"]) * 1000

    total_latency += latency
    count += 1


    print("----------------------")
    print("Received:", data)
    print("Latency:", round(latency, 2), "ms")


    # Stop after receiving all 3 messages
    if count == 3:

        end_time = time.time()

        total_time = end_time - start_time

        throughput = count / total_time

        avg_latency = total_latency / count


        print("\n========== RESULTS ==========")
        print("Total Messages:", count)
        print("Total Time:", round(total_time, 3), "seconds")
        print("Average Latency:", round(avg_latency, 2), "ms")
        print("Throughput:", round(throughput, 2), "messages/sec")

        break
