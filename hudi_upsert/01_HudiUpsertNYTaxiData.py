# update
import sys
from pyspark.context import SparkContext
from pyspark.sql.session import SparkSession
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql.functions import col, to_timestamp, monotonically_increasing_id, to_date, when
from awsglue.utils import getResolvedOptions
from pyspark.sql.types import *
from datetime import datetime

args = getResolvedOptions(sys.argv, ['JOB_NAME'])

spark = SparkSession.builder.config('spark.serializer', 'org.apache.spark.serializer.KryoSerializer')\
    .config('spark.sql.hive.convertMetastoreParquet', 'false')\
    .getOrCreate()

sc = spark.sparkContext
glueContext = GlueContext(sc)
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

yellow_tripdata_schema = StructType(
    [StructField("vendorid", IntegerType(), True),
     StructField("tpep_pickup_datetime", TimestampType(), True),
     StructField("tpep_dropoff_datetime", TimestampType(), True),
     StructField("passenger_count", IntegerType(), True),
     StructField("trip_distance", DoubleType(), True),
     StructField("ratecodeid", IntegerType(), True),
     StructField("store_and_fwd_flag", StringType(), True),
     StructField("pulocationid", IntegerType(), True),
     StructField("dolocationid", IntegerType(), True),
     StructField("payment_type", IntegerType(), True),
     StructField("fare_amount", DoubleType(), True),
     StructField("extra", DoubleType(), True),
     StructField("mta_tax", DoubleType(), True),
     StructField("tip_amount", DoubleType(), True),
     StructField("tolls_amount", DoubleType(), True),
     StructField("improvement_surcharge", DoubleType(), True),
     StructField("total_amount", DoubleType(), True),
     StructField("congestion_surcharge", DoubleType(), True),
     StructField("pk_col", LongType(), True),
    StructField("pickup_date", DateType(), True)])

hudiOptions = {
    "hoodie.table.name": "ny_yellow_trip_data",
    "hoodie.datasource.write.recordkey.field": "pk_col",
    "hoodie.datasource.write.precombine.field": "tpep_pickup_datetime",
    "hoodie.datasource.write.partitionpath.field": "pickup_date",
    "hoodie.datasource.write.hive_style_partitioning": "true",
    'hoodie.consistency.check.enabled': 'true',
    "hoodie.datasource.hive_sync.enable": "true",
    "hoodie.datasource.hive_sync.database": 'default',
    "hoodie.datasource.hive_sync.table": "nyc_hudi_tripdata_table",
    "hoodie.datasource.hive_sync.partition_fields": "pickup_date",
    "hoodie.datasource.hive_sync.partition_extractor_class": "org.apache.hudi.hive.MultiPartKeysValueExtractor",
    "hoodie.datasource.hive_sync.mode": "hms",
    "hoodie.bulkinsert.shuffle.parallelism": 10,
    "hoodie.cleaner.policy": "KEEP_LATEST_COMMITS",
    "hoodie.cleaner.commits.retained": 10,
    "hoodie.index.type": "GLOBAL_BLOOM",
    "hoodie.bloom.index.update.partition.path": "true"
}

initDf = spark.sql("select * from default.ny_yellow_trip_data where vendorid = 1")

updatedDf = initDf.withColumn("vendorid", when(initDf.vendorid == 1, 9))

# Write a DataFrame as a Hudi dataset
updatedDf.write.format("org.apache.hudi")\
    .option("hoodie.datasource.write.operation", "upsert")\
    .options(**hudiOptions)\
    .mode("append")\
    .save(f"s3://olympus-dev-data-nyc-hudi-tripdata-table/hudidataset/")

job.commit()