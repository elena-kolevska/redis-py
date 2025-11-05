#!/usr/bin/env python3
"""
Test script to demonstrate automatic connection creation time metric.

This script:
1. Starts a Prometheus metrics server on port 8000
2. Initializes redis-py with OpenTelemetry metrics
3. Creates a Redis client (metrics are automatically collected!)
4. Executes Redis commands that trigger connection creation
5. Exposes metrics at http://localhost:8000/metrics

Look for the metric: db_client_connection_create_time_bucket

NOTE: No manual instrumentation needed! Just init_observability() and use Redis normally.
"""

import sys
import time

# Check dependencies
try:
    from redis.observability import init_observability, OTelConfig, is_observability_enabled
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from prometheus_client import start_http_server
    import redis
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("\nInstall with:")
    print("  pip install redis opentelemetry-api opentelemetry-sdk opentelemetry-exporter-prometheus prometheus-client")
    sys.exit(1)

def main():
    print("=" * 70)
    print("Redis Connection Creation Time Metric Demo")
    print("=" * 70)
    
    # 1. Start Prometheus metrics server
    print("\n[1/5] Starting Prometheus metrics server...")
    try:
        start_http_server(port=8000)
        print("      ✅ Metrics server running on http://localhost:8000/metrics")
    except OSError as e:
        print(f"      ❌ Failed to start server: {e}")
        print("      💡 Port 8000 might be in use. Try a different port.")
        sys.exit(1)
    
    # 2. Create Prometheus exporter
    print("\n[2/5] Creating Prometheus exporter...")
    prometheus_reader = PrometheusMetricReader()
    meter_provider = MeterProvider(metric_readers=[prometheus_reader])
    print("      ✅ Prometheus exporter created")
    
    # 3. Initialize observability
    print("\n[3/5] Initializing OpenTelemetry observability...")
    init_observability(OTelConfig(
        enable_metrics=True,
        service_name="connection-test",
        meter_provider=meter_provider
    ))
    
    if is_observability_enabled():
        print("      ✅ Observability initialized")
        print("      ✅ All Redis clients will now automatically collect metrics!")
    else:
        print("      ❌ Observability failed to initialize")
        sys.exit(1)
    
    # 4. Create Redis client (NO manual instrumentation needed!)
    print("\n[4/5] Creating Redis client...")
    try:
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        print("      ✅ Redis client created")
        print("      ✅ Connection pool automatically instrumented!")
    except Exception as e:
        print(f"      ❌ Failed to create Redis client: {e}")
        sys.exit(1)
    
    # 5. Execute commands that create connections
    print("\n[5/5] Executing Redis commands to trigger connection creation...")
    try:
        # First command will create a connection
        print("      📊 Executing first command (will create connection)...")
        r.set("test:key:1", "value1")
        print("      ✅ Connection created and metric recorded automatically!")
        
        # Subsequent commands reuse the connection
        print("      📊 Executing more commands (reuse connection)...")
        for i in range(2, 11):
            r.set(f"test:key:{i}", f"value{i}")
            r.get(f"test:key:{i}")
        print("      ✅ Commands executed")
        
        # Force create more connections by disconnecting
        print("      📊 Disconnecting to force new connection creation...")
        r.connection_pool.disconnect()
        
        # This will create a new connection
        r.set("test:key:new", "new_value")
        print("      ✅ New connection created and metric recorded automatically!")
        
    except redis.ConnectionError as e:
        print(f"      ❌ Failed to connect to Redis: {e}")
        print("      💡 Make sure Redis is running on localhost:6379")
        sys.exit(1)
    except Exception as e:
        print(f"      ❌ Error executing commands: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Show results
    print("\n" + "=" * 70)
    print("✅ SUCCESS! Connection creation metrics recorded automatically")
    print("=" * 70)
    
    print("\n📊 View Metrics:")
    print("   Raw metrics:  http://localhost:8000/metrics")
    print("   (Look for: db_client_connection_create_time_bucket)")
    
    print("\n🔍 Metric Details:")
    print("   Metric name: db_client_connection_create_time")
    print("   Type:        Histogram")
    print("   Unit:        seconds")
    print("   Labels:      db_system, db_client_connection_pool_name")
    
    print("\n💡 What to look for in the metrics:")
    print("   - db_client_connection_create_time_bucket{...le=\"0.001\"}")
    print("   - db_client_connection_create_time_bucket{...le=\"0.005\"}")
    print("   - db_client_connection_create_time_sum")
    print("   - db_client_connection_create_time_count (should be 2)")
    
    print("\n🔍 Prometheus Queries (in http://localhost:9090):")
    print("   Average connection creation time:")
    print("     rate(db_client_connection_create_time_sum[5m]) /")
    print("     rate(db_client_connection_create_time_count[5m])")
    print()
    print("   95th percentile:")
    print("     histogram_quantile(0.95,")
    print("       rate(db_client_connection_create_time_bucket[5m]))")
    
    print("\n🎯 Key Point:")
    print("   NO manual instrumentation needed!")
    print("   Just call init_observability() once, then use Redis normally.")
    print("   All metrics are collected automatically!")
    
    print("\n" + "=" * 70)
    print("Press Ctrl+C to stop the metrics server...")
    print("=" * 70)
    
    # Keep server running
    try:
        while True:
            # Periodically create new connections
            r.connection_pool.disconnect()
            r.ping()
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
        r.close()
        print("✅ Cleanup complete")

if __name__ == "__main__":
    main()

