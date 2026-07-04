from fastapi import FastAPI, HTTPException, Request
import yaml
import os
import subprocess
import signal
import tempfile
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("otel-dynamic-configurer")

app = FastAPI()

# Read Env Vars
BASE_FIXED_CONFIG = os.getenv("BASE_FIXED_CONFIG")
DYNAMIC_CONFIG = os.getenv("DYNAMIC_CONFIG")

# API to write OpenTelemetry Collector configuration to PVC
# This API validates the config using otelcol-contrib before writing it to the file
# It also sends a SIGHUP to the otelcol-contrib process to reload the configuration
# The config is expected to be in YAML format
# If the config is unchanged, it returns a status of "no-change"
# If the config is changed and successfully written, it returns a status of "updated"
# If the validation fails, it raises an HTTPException with a 400 status code and the validation error message
@app.post("/otel/config")
async def write_config(request: Request):
    logger.info(f"Received config update request")

    # Read raw body as bytes and load as YAML
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")
    try:
        config_content = yaml.safe_load(body_str)
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid YAML format: {e}"
        )

    if not isinstance(config_content, dict):
        logger.error("YAML body is not a dictionary/map")
        raise HTTPException(
            status_code=400,
            detail="YAML configuration must be a map/dictionary"
        )

    # Load existing config if it exists
    config_changed = True
    if os.path.isfile(DYNAMIC_CONFIG):
        try:
            with open(DYNAMIC_CONFIG, "r") as f:
                existing_content = yaml.safe_load(f)
            if existing_content == config_content:
                config_changed = False
                logger.info("Config file unchanged. Skipping update.")
        except Exception:
            pass  # Treat error as a change

    if not config_changed:
        return {"status": "no-change", "file": DYNAMIC_CONFIG}

    # Before using this new config, Validate the config using otelcol-contrib
    try:
        logger.info(f"Validating config using otelcol-contrib")
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".yaml") as tmpfile:
            yaml.dump(config_content, tmpfile)
            tmpfile_path = tmpfile.name

        result = subprocess.run(
            ["otelcol-contrib", "--config", BASE_FIXED_CONFIG, "--config", tmpfile_path, "validate"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            logger.error("otelcol-contrib config validation failed")
            raise HTTPException(
                status_code=400,
                detail=f"Config validation failed:\n{result.stderr}"
            )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Validation timed out")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Validation error: {e}")
    finally:
        if os.path.exists(tmpfile_path):
            os.remove(tmpfile_path)

    # Write the validated config
    try:
        with open(DYNAMIC_CONFIG, "w") as f:
            yaml.dump(config_content, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing file: {e}")

    # Send SIGHUP to otelcol-contrib
    try:
        pid_output = subprocess.check_output(["pgrep", "-f", "otelcol-contrib"])
        pid = int(pid_output.decode().splitlines()[0])
        os.kill(pid, signal.SIGHUP)
        logger.info(f"Sent SIGHUP to otelcol-contrib (PID: {pid})")
    except subprocess.CalledProcessError:
        logger.error("otelcol-contrib process not found")
        raise HTTPException(status_code=500, detail="otelcol-contrib process not found")
    except Exception as e:
        logger.error(f"Failed to send SIGHUP: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send SIGHUP: {e}")

    return {"status": "updated", "file": DYNAMIC_CONFIG, "signal_sent_to_pid": pid}
