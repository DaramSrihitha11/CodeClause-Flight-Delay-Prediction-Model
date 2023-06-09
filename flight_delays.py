# -*- coding: utf-8 -*-
"""flight_delays.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1MPYsG7M1MN-DJ3n8d3hWMbcsz9YIgme6

# Flight Delay Prediction Model
BY : SRIHITHA DARAM
## Summary :
The Flight Delay Prediction Model implemented in Google Colab uses historical flight data to predict whether a flight will experience delays. Here is a summary of the model:

1. **Data Preprocessing:** The provided flight data is preprocessed to prepare it for training the model. This includes handling missing values, encoding categorical variables, and splitting the data into training and testing sets.

2. **Feature Selection:** Relevant features are selected from the dataset based on their potential impact on flight delays. These features may include the day of the month, day of the week, airline carrier, origin and destination airports, and other relevant information.

3. **Model Training:** The selected features and corresponding flight delay labels are used to train a machine learning model. Various algorithms can be applied, such as decision trees, random forests, or gradient boosting, to learn patterns and relationships between the features and flight delays.

4. **Model Evaluation:** The trained model is evaluated using the testing dataset to assess its performance in predicting flight delays. Common evaluation metrics include accuracy, precision, recall, and F1 score. The model's performance is compared to baseline models or industry standards to determine its effectiveness.

5. **Model Deployment:** Once the model has been trained and evaluated, it can be deployed to make real-time predictions on new flight data. This can be integrated into an application or system to provide users with timely information about potential flight delays.

6. **Improvement Iterations:** The model's performance can be further improved by fine-tuning hyperparameters, incorporating additional features, or exploring advanced techniques such as ensemble learning or neural networks. Iterative improvements are made to enhance the model's predictive capabilities.

Overall, the Flight Delay Prediction Model implemented in Google Colab enables the prediction of flight delays based on historical flight data. By leveraging machine learning algorithms, the model can provide valuable insights to airlines, passengers, and other stakeholders, helping them make informed decisions and mitigate the impact of flight delays.

## Spark and Colaboratory setup
"""

# Install spark-related depdencies for Python

!apt-get install openjdk-8-jdk-headless -qq > /dev/null
!wget -q http://apache.osuosl.org/spark/spark-2.4.3/spark-2.4.3-bin-hadoop2.7.tgz
!tar xf spark-2.4.3-bin-hadoop2.7.tgz

!pip install -q findspark
!pip install pyspark

# Set up required environment variables

import os
os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-8-openjdk-amd64"
os.environ["SPARK_HOME"] = "/content/spark-2.4.3-bin-hadoop2.7"

# Point Colaboratory to your Google Drive

from google.colab import drive
drive.mount('/content/gdrive')

"""## Data download to Google Drive"""

# Download datasets directly to your Google Drive "Colab Datasets" folder

import requests

# 2007 data

file_url = "http://stat-computing.org/dataexpo/2009/2007.csv.bz2"

r = requests.get(file_url, stream = True) 

with open("/content/gdrive/My Drive/Colab Datasets/2007.csv.bz2", "wb") as file: 
	for block in r.iter_content(chunk_size = 1024): 
		if block: 
			file.write(block)

# 2008 data

file_url = "http://stat-computing.org/dataexpo/2009/2008.csv.bz2"

r = requests.get(file_url, stream = True) 

with open("/content/gdrive/My Drive/Colab Datasets/2008.csv.bz2", "wb") as file: 
	for block in r.iter_content(chunk_size = 1024): 
		if block: 
			file.write(block)

"""##  **Import** tools from PySpark

"""

# Tools we need to connect to the Spark server, load our data, clean it, and prepare, execute, and evaluate a model

from pyspark import SparkContext
from pyspark.sql import SparkSession

from pyspark.ml import Pipeline
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.feature import IndexToString, StringIndexer, VectorIndexer, VectorAssembler
from pyspark.ml.evaluation import MulticlassClassificationEvaluator

from pyspark.sql.functions import isnan, when, count, col

"""## Set Constants"""

CSV_2007= "/content/gdrive/My Drive/Colab Datasets/2007.csv.bz2" 
CSV_2008= "/content/gdrive/My Drive/Colab Datasets/2008.csv.bz2"
APP_NAME = "Flight Delays"
SPARK_URL = "local[*]"
RANDOM_SEED = 141109
TRAINING_DATA_RATIO = 0.7
RF_NUM_TREES = 8
RF_MAX_DEPTH = 4
RF_NUM_BINS = 32

"""## Connect to the server and load data"""

# Connect to the Spark server

spark = SparkSession.builder.appName(APP_NAME).master(SPARK_URL).getOrCreate()

# Load datasets

df_2007 = spark.read.options(header="true",inferschema = "true").csv(CSV_2007)
df_2008 = spark.read.options(header="true",inferschema = "true").csv(CSV_2008)

# We concatenate both datasets

df = df_2007.unionAll(df_2008)

"""## Prepare, clean and validate the data


"""

# What's the data shape before starting cleaning ?

print(f"The shape is {df.count():d} rows by {len(df.columns):d} columns.")

# What's the number of null values ?

null_counts = df.select([count(when(isnan(c) | col(c).isNull(), c)).alias(c) 
                         for c in df.columns]).toPandas().to_dict(orient='records')

print(f"We have {sum(null_counts[0].values()):d} null values in this dataset.")

# Drop null columns and inputs ?

df = df.drop(df.CancellationCode)
df = df.na.drop()

# Confirm there are no null values

null_counts = df.select([count(when(isnan(c) | col(c).isNull(), c)).alias(c) 
                         for c in df.columns]).toPandas().to_dict(orient='records')

print(f"We have {sum(null_counts[0].values()):d} null values in this dataset.")

# What's the data shape after cleaning ?

print(f"The shape is {df.count():d} rows by {len(df.columns):d} columns.")

"""## Set up and run our classifier in Spark"""

# What are the column's type ?

df.dtypes

# Create list of feature columns

feature_cols = ['Year', 'Month', 'DayofMonth', 'DayOfWeek', 'CRSDepTime', 
                'CRSArrTime', 'FlightNum', 'Distance', 'Diverted']

# Generate and create our new feature vector column

df = VectorAssembler(inputCols=feature_cols, outputCol="features").transform(df)

# Select input columns

df.select("Cancelled", "features").show(5)

# Build the training indexers

# Generate a labelIndexer
labelIndexer = StringIndexer(inputCol="Cancelled", outputCol="indexedLabel").fit(df)

# Generate the indexed feature vector
featureIndexer = VectorIndexer(inputCol="features", outputCol="indexedFeatures", maxCategories=4).fit(df)
    
# Split the data into training and tests sets
(trainingData, testData) = df.randomSplit([TRAINING_DATA_RATIO, 1 - TRAINING_DATA_RATIO])

# Train the RandomForest model
rf = RandomForestClassifier(labelCol="indexedLabel", featuresCol="indexedFeatures", numTrees=RF_NUM_TREES)

# Chain indexers and the forest models in a Pipeline
pipeline = Pipeline(stages=[labelIndexer, featureIndexer, rf])

# Train the model

model = pipeline.fit(trainingData)

# Make predictions

predictions = model.transform(testData)

"""## Evaluate our model"""

# Select prediction, true label and compute test error
evaluator = MulticlassClassificationEvaluator(
    labelCol="indexedLabel", predictionCol="prediction", metricName="accuracy")
accuracy = evaluator.evaluate(predictions)

print(f"Test Error = {(1.0 - accuracy):g}")
print(f"Accuracy = {accuracy:g}")