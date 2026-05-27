import time
import os
from kafka import KafkaProducer
import json
import pandas as pd
from loguru import logger
from dotenv import load_dotenv
load_dotenv(".env")
env = os.environ
import argparse


def simulate_kafka_stream(
    csv_path,
    topic="test_topic",
    bootstrap_servers="kafka:29092",
    key_field=None,
    delay=0.01
):
    df = pd.read_csv(csv_path).head(100000)
    logger.info(f"Loaded CSV: {len(df)} rows. Streaming to '{topic}'...")

    producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    records = df.to_dict(orient="records") 
    for record in records:
        producer.send(topic, value=record)
        logger.info(f"[KAFKA PRODUCER] Sending the following:  {record}")
        producer.flush()
        time.sleep(delay) 

    producer.close()
    logger.info("Test stream finalized")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["categorical", "numerical"], default=None)
    parser.add_argument("--topic", default=None)
    parser.add_argument("--bootstrap-servers", default="kafka:29092")
    args = parser.parse_args()

    mode = args.mode or os.environ.get("STREAM_MODE", "numerical")
    topic = args.topic or os.environ.get("STREAM_TOPIC", "st-viz-topic")

    if mode == "categorical":
        simulate_kafka_stream(env['CATEGORICAL_SUBSET_DEMO_STREAMER'], topic, args.bootstrap_servers)
    elif mode == "numerical":
        simulate_kafka_stream(env['NUMERICAL_SUBSET_DEMO_STREAMER'], topic, args.bootstrap_servers)