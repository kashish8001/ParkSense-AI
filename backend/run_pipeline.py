"""Run the ParkSense data processing pipeline."""

from app.services.pipeline_service import run_pipeline


if __name__ == "__main__":
    result = run_pipeline()
    print(result)
