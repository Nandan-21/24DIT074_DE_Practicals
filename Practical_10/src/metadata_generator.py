from pathlib import Path
import pandas as pd

def generate_device_metadata(output_path: Path, num_devices: int = 20) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    models = ["EdgeSensor-X1", "IndustrialGate-9000", "ThermoSpy-V2", "VibeMonitor-Pro"]
    zones = ["Zone-A_Assembly", "Zone-B_Packaging", "Zone-C_ColdStorage", "Zone-D_PowerPlant"]
    criticalities = ["HIGH", "MEDIUM", "LOW"]

    devices = []
    for i in range(1, num_devices + 1):
        dev_id = f"DEV-{i:03d}"
        devices.append({
            "device_id": dev_id,
            "device_model": models[i % len(models)],
            "facility_zone": zones[i % len(zones)],
            "criticality": criticalities[i % len(criticalities)],
            "max_operating_temp": 85.0 if i % 2 == 0 else 95.0
        })

    df = pd.DataFrame(devices)
    df.to_csv(output_path, index=False)
    return output_path
