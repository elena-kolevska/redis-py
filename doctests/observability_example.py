# EXAMPLE: opentelemetry_metrics
# HIDE_START
"""
Code samples for OpenTelemetry observability in redis-py.

This example demonstrates how to enable OpenTelemetry metrics collection
for Redis operations, including connection pool metrics and command execution metrics.

Prerequisites:
    pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-http

Note: This example requires an OpenTelemetry collector running at http://localhost:4318
You can start one using Docker:
    docker run -p 4318:4318 otel/opentelemetry-collector
"""
import random
import time

# HIDE_END

import os
import redis
from redis.observability import get_observability_instance, OTelConfig

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.semconv.resource import ResourceAttributes

def setup_external_otel_sdk(exporter_type="otlp", log_file=None):
   """
   Setup OpenTelemetry SDK with configurable exporter for debugging.

   Args:
       exporter_type: Type of exporter to use. Options:
           - "otlp": Export to OTLP collector (default, production use)
           - "console": Print metrics to console (debugging)
           - "file": Write metrics to a file (debugging)
       log_file: Path to log file when exporter_type="file".
                 Defaults to "otel_metrics.log" if not specified.
   """
   # Configure the resource with service info
   resource = Resource.create({
       ResourceAttributes.SERVICE_NAME: os.getenv("OTEL_SERVICE_NAME", "otel-metrics-demo"),
       ResourceAttributes.SERVICE_VERSION: "0.1.0",
   })

   # Create the appropriate exporter based on type
   if exporter_type == "console":
       # Console exporter - prints metrics to stdout
       exporter = ConsoleMetricExporter()
       print("🔍 Debug mode: Metrics will be printed to console")
   elif exporter_type == "file":
       # File exporter - writes metrics to a file
       import sys
       log_path = log_file or "otel_metrics.log"
       log_file_handle = open(log_path, "w")
       exporter = ConsoleMetricExporter(out=log_file_handle)
       print(f"🔍 Debug mode: Metrics will be written to {log_path}")
   else:  # "otlp" or default
       # OTLP exporter - sends to collector
       exporter = OTLPMetricExporter(
           endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318") + "/v1/metrics"
       )
       print(f"🔍 : Metrics will be sent to OTLP collector at {exporter._endpoint}")

   # Create a metric reader that will periodically export metrics
   reader = PeriodicExportingMetricReader(
       exporter=exporter,
       export_interval_millis=3000  # Export every 3 seconds
   )

   # Initialize the MeterProvider with resource and reader
   provider = MeterProvider(resource=resource, metric_readers=[reader])

   # Set the global MeterProvider
   metrics.set_meter_provider(provider)

   return provider



# Initialize OpenTelemetry SDK
# Choose one of the following options:

# Option 1: OTLP exporter (production) - sends to collector
# meter_provider = setup_external_otel_sdk(exporter_type="otlp")

# Option 2: Console exporter (debugging) - prints to stdout
# meter_provider = setup_external_otel_sdk(exporter_type="file")

# Option 3: File exporter (debugging) - writes to file
# meter_provider = setup_external_otel_sdk(exporter_type="file", log_file="redis_metrics.log")
meter_provider = setup_external_otel_sdk()

# STEP_START basic_config
# Get singleton instance
otel = get_observability_instance()

# Initialize observability ONCE at application startup
# Note: We already set up the global MeterProvider above via setup_external_otel_sdk()
otel.init(OTelConfig(
    enable_metrics=True,
))

print("✅ Observability initialized - using global MeterProvider")
print("📊 Metrics will be exported to the configured exporter")

# Now ALL Redis clients automatically collect metrics - no config needed!
r = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True
)

# STEP_END

# STEP_START basic_operations
# Perform some Redis operations - metrics will be automatically collected

for i in range(15):
    # pipe = r.pipeline()
    random_number = random.randint(1, 50)
    for j in range(random_number):
        r.set(f"user:1001-{i}", "Jane Smith")
        r.set(f"user:1002-{i}", "Bob Johnson")
        r.get(f"user:1001-{i}")
    # results = pipe.execute()
    time.sleep(0.5)


print(f"Set and retrieved {i} names and pipes")
# >>> Retrieved: John Doe


# Pipeline operations are also tracked
# >>> Pipeline results: [True, True, 'Jane Smith']
# STEP_END

# STEP_START cleanup
# Close the connection when done
r.close()

# At application shutdown, flush and shutdown observability
otel.shutdown()
# STEP_END

# HIDE_START
print("\nOpenTelemetry observability example completed!")
print("\nMetrics collected include:")
print("  - Connection pool metrics (count, wait time, use time)")
print("  - Command execution duration")
print("  - Error rates and types")
print("  - Cluster redirections (for cluster mode)")
print("\nView metrics in your OpenTelemetry collector or observability platform.")
# HIDE_END

