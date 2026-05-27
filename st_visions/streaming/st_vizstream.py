'''
    st_vizstream.py - v2025.09.27

    Authors: Paraschos Moraitis, Andreas Tritsarolis
'''

import threading
import time
import json
from abc import ABC, abstractmethod
from queue import Queue
from loguru import logger

from kafka import KafkaConsumer
from kafka.admin import KafkaAdminClient, NewTopic

class ST_AbstractStream(ABC):
    """
    Abstract base class for spatio-temporal data streaming implementations.
    
    Provides the framework for real-time data consumption from various streaming
    sources. Designed to support visualization of live spatio-temporal data streams.
    
    Parameters
    ----------
    topic_name : str
        Name of the topic/stream channel to consume data from.
    
    Attributes
    ----------
    topic : str
        Stream topic/channel identifier.
    consumer : object or None
        Stream client connection object (implementation-specific).
    _thread : threading.Thread or None
        Background thread for data consumption.
    _stop : bool
        Control flag for stopping the consumption thread.
    data_queue : Queue
        Thread-safe queue for buffering incoming data records.
    max_queue_size : int or None
        Maximum number of records to buffer (None for unlimited).
    
    Notes
    -----
    This is part of the ST_Visions+ fork extending the original library with
    real-time streaming capabilities for spatio-temporal analytics.
    
    Subclasses must implement the abstract methods for specific streaming
    protocols.
    
    See Also
    --------
    ST_KafkaStream : Kafka-specific implementation.
    """

    def __init__(self):
        self.consumer = None
        self._thread = None
        self._stop = False
        self.data_queue = Queue()
        self.max_queue_size = None


    @abstractmethod
    def _connect(self):
        """
        Initialize stream connection to the data provider.
        
        This method must establish the connection to the streaming service
        (e.g., Kafka broker) and prepare the consumer for
        receiving messages.
        
        Raises
        ------
        ConnectionError
            If connection to the streaming service fails.
        ValueError
            If required configuration parameters are missing or invalid.

        """
        pass

    @abstractmethod
    def _poll_data(self):
        """
        Poll and process incoming data from the stream.

        """
        pass

    @abstractmethod
    def fetch_data(self, max_points):
        """
        Retrieve buffered data for visualization.
        
        Parameters
        ----------
        max_points : int
            Maximum number of data points to return. If more points are
            buffered, returns the most recent `max_points` records.
        
        Returns
        -------
        dict or None
            Dictionary with column-oriented data (orient='list') where keys
            are field names and values are lists of field values. Returns
            None if no data is available.
        
        Notes
        -----
        This method drains the current queue contents. Subsequent calls
        will only return new data received after the previous call.
        """
        pass


    def _consume_loop(self):
        """
        Main data consumption loop running in background thread.
        
        Establishes connection, then continuously polls for new data until
        stopped. Handles connection errors and ensures proper cleanup.
        
        Notes
        -----
        This method runs in a separate daemon thread started by `start()`.
        It includes a small sleep (50ms) between poll cycles to prevent
        excessive CPU usage.
        
        """
        try:
            self._connect()
        except Exception as e:
            logger.info(f"[STREAM ERROR] Failed to connect: {e}")
            return 

        try:
            while not self._stop:
                self._poll_data()
                time.sleep(0.05)
        except Exception as e:
            logger.info(f"[STREAM ERROR] {e}")
        finally:
            self._close()


    def start(self):
        """
        Start background thread for data consumption.
        
        Initializes and starts a daemon thread that runs `_consume_loop()`.
        If the stream is already running, logs a message and returns.

        """
        if self._thread and self._thread.is_alive():
            logger.info("Stream already running.")
            return

        self._stop = False
        self._thread = threading.Thread(target=self._consume_loop, daemon=True)
        self._thread.start()
        logger.info("Stream thread initialized")

    def stop(self):
        """
        Stop background thread and clean up resources.
        
        Signals the consumption thread to stop and waits up to 5 seconds
        for it to terminate. Closes the stream connection and releases
        resources.

        """

        logger.info("Stopping stream...")
        self._stop = True
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Stream stopped")

    def _close(self):
        """
        Clean up stream connection resources.
        
        Safely closes the stream consumer connection if it exists.
        Suppresses any exceptions during closure to ensure the thread
        can exit cleanly.
        """
        if self.consumer:
            try:
                self.consumer.close()
            except Exception:
                pass



class ST_KafkaStream(ST_AbstractStream):
    """
    Kafka-based implementation for spatio-temporal data streaming based on the abstract class ST_AbstractStream.
    
    Consumes messages from Apache Kafka topics containing spatio-temporal
    data (e.g., GPS coordinates). Automatically creates
    topics if they don't exist and buffers data for visualization.
    
    Parameters
    ----------
    topic_name : str, optional (Default: ``default-topic``).
        Kafka topic to consume from. 
    bootstrap_servers : str, optional  (Default: ``localhost:9092``).
        Kafka broker addresses (comma-separated).
    group_id : str, optional  (Default: ``stream-group``).
        Consumer group identifier.
    max_queue_size : int, optional (Default: ``10000``)
        Maximum number of records to buffer. When exceeded, oldest records
        are discarded.
    
    Attributes
    ----------
    bootstrap_servers : str
        Kafka broker connection string.
    group_id : str
        Consumer group ID for Kafka.
    
    Notes
    -----
    Requires `kafka-python` package. Messages must be JSON-encoded with
    at minimum 'lon' (longitude) and 'lat' (latitude) fields to be processed.
    Automatically starts consuming upon initialization.
    """

    def __init__(self, topic_name="default-topic", bootstrap_servers="localhost:9092", group_id="stream-group", max_queue_size = 10000, lon_field="lon", lat_field="lat"):
        super().__init__()
        self.topic = topic_name
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.max_queue_size = max_queue_size
        self.lon_field = lon_field   # moved back in from earlier
        self.lat_field = lat_field

        self._assert_topic()
        self.start()

    def _assert_topic(self):
        """
        Ensure Kafka topic exists, creating it if necessary.
        
        Checks if the configured topic exists in the Kafka cluster and
        creates it with default settings (1 partition, 1 replica) if it
        doesn't.
        
        Raises
        ------
        KafkaError
            If unable to connect to Kafka admin interface or create topic.
        
        """
        admin = KafkaAdminClient(bootstrap_servers=self.bootstrap_servers)
        existing = admin.list_topics()

        if self.topic not in existing:
            logger.info(f"Creating topic '{self.topic}'...")
            new_topic = NewTopic(name=self.topic, num_partitions=1, replication_factor=1)
            admin.create_topics(new_topics=[new_topic])
        else:
            logger.info(f"Topic '{self.topic}' exists.")
        admin.close()

    def _connect(self):
        """
        Initialize Kafka consumer connection.
        
        Creates and configures a KafkaConsumer instance with JSON
        deserialization and appropriate consumer group settings.
        
        Raises
        ------
        KafkaConnectionError
            If unable to connect to Kafka brokers.
        ConfigurationError
            If consumer configuration is invalid.
        """
        self.consumer = KafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            key_deserializer=lambda k: k.decode() if k else None,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
        )
        logger.info(f"Connected to stream successfully! Listening to '{self.topic}'")

    def fetch_data(self, max_points=500):
        """
        Retrieve buffered Kafka messages for visualization.
        
        Parameters
        ----------
        max_points : int, optional (Default: ``500``)
            Maximum number of recent data points to return.
        
        Returns
        -------
        dict or None
            Dictionary with column-oriented data (orient='list') where keys
            are field names and values are lists of field values. Returns
            None if no data is available.

        Notes
        -----
        This method drains the current queue. The returned dictionary is
        optimized for use with pandas DataFrame construction (pd.DataFrame(data)).
        """
        if self.data_queue.empty():
            return None

        records = []
        while not self.data_queue.empty():
            records.append(self.data_queue.get())

        if not records:
            return None

        data = {k: [] for k in records[0].keys()}
        for record in records:
            for k, v in record.items():
                data[k].append(v)

        for k in data.keys():
            data[k] = data[k][-max_points:]

        return data

    def _poll_data(self):
        """
        Poll Kafka for new messages and queue valid spatio-temporal data.
        
        Fetches messages from Kafka with 500ms timeout, validates required
        fields (longitude and latitude), and adds to queue. Maintains queue
        size limit by discarding oldest messages when the limit is exceeded.
        
        """
        msg_pack = self.consumer.poll(timeout_ms=500)
        for tp, messages in msg_pack.items():
            for msg in messages:
                value = msg.value
                lon = value.get(self.lon_field)
                lat = value.get(self.lat_field)

                if lon is None or lat is None:
                    continue

                # insert to queue check 
                if self.data_queue.qsize() >= self.max_queue_size:
                    _ = self.data_queue.get()
                self.data_queue.put(value)
            