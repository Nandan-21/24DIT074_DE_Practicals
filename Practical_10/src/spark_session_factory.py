import os
from pathlib import Path
from pyspark.sql import SparkSession

def get_spark_session(app_name: str = "Practical10_Transformations") -> SparkSession:
    """Configures and returns a local PySpark SparkSession with Windows Hadoop support."""
    # Configure HADOOP_HOME for Windows FileOutputCommitter support
    project_root = Path(__file__).resolve().parent.parent.parent
    hadoop_dir = project_root / "hadoop"
    if hadoop_dir.exists():
        os.environ["HADOOP_HOME"] = str(hadoop_dir)
        bin_dir = str(hadoop_dir / "bin")
        if bin_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")

    return (
        SparkSession.builder
        .master("local[2]")
        .appName(app_name)
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.default.parallelism", "2")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.driver.memory", "1g")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
