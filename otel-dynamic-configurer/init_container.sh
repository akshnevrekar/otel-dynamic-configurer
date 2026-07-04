#!/bin/sh
# This script initializes the OpenTelemetry Collector configuration using init container
# This script copies the default dynamic config to PVC if one doesn't already exist

if [ ! -f "$DYNAMIC_CONFIG" ]; then
    echo "Copying initial dynamic-config.yaml to persistent volume"
    cp "$BASE_DYNAMIC_CONFIG" "$DYNAMIC_CONFIG"
else
    echo "Config already exists at $DYNAMIC_CONFIG, skipping copy"
fi

# Step 2: Validate existing config
# This will handle if the config is invalid and replace it with the base dynamic config with NOP exporter
otelcol-contrib --config "$BASE_FIXED_CONFIG" --config "$DYNAMIC_CONFIG" validate
if [ $? -ne 0 ]; then
    echo "Validation failed. Replacing with base dynamic config."
    cp "$BASE_DYNAMIC_CONFIG" "$DYNAMIC_CONFIG"
else
    echo "Validation passed. No action needed."
fi