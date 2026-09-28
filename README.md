# Project IRIS - Canonical PostGIS Pilot Schema

Minimum reproducible PostgreSQL 16 / PostGIS 3.4 schema supporting automated land prospecting across BESS (Battery Energy Storage Systems) and Peatland Restoration verticals.

Objective - determining whether a specific piece of land is commercially viable for battery storage (BESS) and/or environmental restoration (peatland credits)

---

## 1. Quickstart & One-Command Rebuild

### Prerequisites
- Python 3.12+
- Docker and Docker Compose
- `make`

### Installation & Execution
```bash
# 1. Create and activate virtual environment
python -m venv .venv
# With powershell
.venv\Scripts\Activate.ps1

#For cmd
.\.venv\Scripts\activate.bat


# 2. Install dependencies
pip install -e .

# 3. Complete zero-touch teardown, migration, seed, query verification, and testing
make reset

# OR Can use the make file or make commands from run.py
python run.py reset


# EPSG:4326 is the standard storage CRS choice as Project IRIS is explicitly designed as a multi-country system