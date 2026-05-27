# Examples

This directory contains notebooks and python scripts showcasing the capabilities of the ST_Visions library

## Prerequisites
- Python 3.10+ 
    - The examples in this repository were developed and tested using Python 3.10.12. Other Python 3 versions may work but are not officially tested.
- Docker Compose
    - Not required for the static data examples, used for the streaming examples.
- Jupyter Notebook 6.x 

## Setup
The following setup also involves the configuration of the docker containers needed for the streaming examples, which is optional when executing the static data examples.

### 1. Set up your environment
create a `data` folder for your datasets inside the `examples` folder and a `.env` file containing the paths to your datasets. Alternatively, you can always directly input a filepath for static data (e.g., CSV file) as well.

```
# example variables from the thesis demos, 
# be advised that the "categorical" dataset path assumes
# at least once categorical column 

# for python scripts and jupyter notebooks we have to go one level back to access the data
NUMERICAL_SUBSET_DEMO = ..\data\your_numerical_dataset.csv
CATEGORICAL_SUBSET_DEMO = ..\data\your_categorical_dataset.csv

# for the data_streamer.py we can access the folder directly
NUMERICAL_SUBSET_DEMO_STREAMER = data\your_numerical_dataset.csv
CATEGORICAL_SUBSET_DEMO_STREAMER = data\your_categorical_dataset.csv

# note: if the data_streamer.py script is ran through a container (see: Configure your docker containers), you may need to alter this path
# according to the docker directory needs. The paths below are the default ones with the given Dockerfile.

NUMERICAL_SUBSET_DEMO_STREAMER = /app/data/your_numerical_dataset.csv
CATEGORICAL_SUBSET_DEMO_STREAMER = /app/data/your_categorical_dataset.csv
```

### 2. Configure the docker containers

Firstly, initialize the kafka image 
```bash
docker compose up -d zookeeper kafka
```

Optionally (but recommended), build the the python container containing the `data_streamer.py` script. 

```bash
docker compose build
```

### 3. Run the Data Streamer

The `data_streamer.py` script is used for the live streaming demo. It simulates a real-time AIS data feed by publishing messages to a Kafka topic.

You can run it either in your local Python environment or inside a containerized environment.

---

### Modes
The script supports the following streaming modes

- `numerical`: dataset contains numerical features  
- `categorical`: dataset includes at least one categorical feature column. 

---

### Local Machine
```bash
python data_streamer.py --mode <streaming_mode> --topic <kafka_topic_name> --bootstrap-servers <kafka_broker_host:port>
```
Example:

```bash
python data_streamer.py --mode numerical --topic local-topic --bootstrap-servers localhost:9092
```

### Docker Container
Docker uses environment variables instead of CLI arguments.

```bash
# Docker Container
docker compose run --rm --env STREAM_MODE=<streaming_mode> --env STREAM_TOPIC=<kafka_topic_name> data-streamer
```
Example:

```bash
docker compose run --rm --env STREAM_MODE=categorical --env STREAM_TOPIC=docker-topic data-streamer
```

### 4. Run a Demo

the `examples` folder includes both **static demos** and **live streaming demos**.

---

### Static Demos

Static data demos do not require a running data streamer.

You can run them by either:

- Opening a Jupyter notebook in the `ipynb/` directory  
- Running a standalone Python script from the `py/` directory  

---

### Live Streaming Demos

Live streaming demos require a running data stream that feeds data into the visualization.

#### Recommended Order of Execution

While the order is not strictly required, it is recommended to:

1. Start the visualization (Bokeh server)
2. Start the data streamer

This ensures the visualization is ready to receive incoming data immediately.

---

### Example Setup

#### 1. Start the Bokeh server 

```bash
bokeh serve --show PY6a-streaming.py
```
This will open a browser window with the streaming visualization.

---
#### 2. Start the data streamer

Once the visualization window is open and waiting for data:

```bash
# Note: numerical is the default streaming mode of the data streamer, but is showcased here.
docker compose run --rm --env STREAM_MODE=numerical data-streamer
```

---

### Stopping the Demo

To stop the streaming demo press `CTRL + C` on both the data streamer and the terminal running the `bokeh serve` command

Then terminate the kafka container
```bash
docker compose down
```

### Notes 
* The streaming visualization depends on an active data stream; without it, the figure will remain idle.
* For best results, stop the data streamer before shutting down the Bokeh server.


## Notebooks

| Name | Description |
|------|-------------|
| LD-1 Visualization | Introductory notebook to basic visualization tasks with ST_Visions|
| LD-2 Data Colorization | Colormapping features |
| LD-3 Advanced Use Cases| Several advanced use cases using the library e.g. chloropleths, multiple datasets, etc. |
| LD-4 Streaming| Live data streaming showcase on a Jupyter notebook |

## Scripts

| Name | Description |
|------|-------------|
| PY1-simple_visualization | A basic ST_Vision static dataset figure |
| PY2-numerical_filter | Applying a numerical filter on a static dataset |
| PY3-filter_interaction | Showcase Filter interaction between multiple filters on a static dataset |
| PY4-colorization| Data colormapping example |
| PY5-data_table| Example figure with accompanying data table |
| PY6a-streaming| Basic data streaming example |
| PY6b-streaming_express| Basic data streaming example usiong the express module |
| PY7a-streaming_numerical_filter | Data streaming with an active numerical filter  |
| PY7b-streaming_multiple_filters | Categorical and numemrical filter interaction on the categorical subset |
| PY7c-streaming_numerical_filter_colormap | Data streaming with an active numerical filter and a numerical colormap |
| PY8-multiple_datasets | Handling multiple datasets on the same figure |


