# Traffic Lights Processor

Advanced GIS analysis tool for intelligent geometric selection and clustering of traffic lights across multiple countries and regions.

## Overview

This tool processes geographic data to:
- **Load and analyze traffic light point geometries** from CSV files
- **Process road network geometries** from GPKG files
- **Apply geographic buffer zones** for spatial filtering
- **Perform intelligent geometric selection** of traffic lights intersecting buffer zones
- **Group traffic lights intelligently** based on spatial proximity (50-70 objects per group)
- **Ensure cluster integrity** - objects from the same intersection always belong to the same group
- **Generate comprehensive reports** with processing statistics

## Key Features

✅ **Geometric Selection**
- Identify roads intersecting buffer polygons
- Filter traffic lights intersecting buffer zones
- Export unmatched points to `output_2_unmatched.gpkg`

✅ **Intelligent Grouping Algorithm**
- DBSCAN clustering for geographic proximity analysis
- Hierarchical subdivision of large clusters
- Groups sized between 50-70 objects (±10)
- Intersection-aware grouping prevents splitting

✅ **Multi-Country Support**
- Flexible CRS (Coordinate Reference System) configuration
- Support for regional or country-wide analysis
- Extensible architecture for various data sources

✅ **Production Ready**
- Comprehensive logging system
- Error handling and recovery
- Detailed processing reports
- Ready-to-run on any laptop

## Requirements

- **Python:** 3.8 or higher
- **System:** Windows, macOS, or Linux
- **RAM:** 2GB minimum (4GB+ recommended)
- **Disk Space:** ~500MB for data and dependencies

### Python Dependencies

```
geopandas>=0.12.0
pandas>=1.5.0
numpy>=1.23.0
scipy>=1.9.0
scikit-learn>=1.1.0
shapely>=2.0.0
fiona>=1.9.0
pyogrio>=0.6.0
```

## Quick Start (5 minutes)

### Step 1: Clone Repository

```bash
git clone https://github.com/kamillisek-tomtom/Traffic-Lights-Processor.git
cd Traffic-Lights-Processor
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Prepare Data

```bash
mkdir -p data/input
# Place your files in data/input/:
# - traffic_lights.csv
# - roads.gpkg
# - buffers.gpkg
```

### Step 5: Configure

Edit `config.json` to match your data column names and CRS.

### Step 6: Run

```bash
python traffic_lights_processor.py
```

## Configuration

### config.json

```json
{
  "crs": "EPSG:4326",
  "input_files": {
    "traffic_lights_csv": "data/input/traffic_lights.csv",
    "roads_gpkg": "data/input/roads.gpkg",
    "buffers_gpkg": "data/input/buffers.gpkg"
  },
  "csv_columns": {
    "lon": "longitude",
    "lat": "latitude"
  },
  "grouping": {
    "min_group_size": 50,
    "max_group_size": 70,
    "epsilon": 1000,
    "min_samples": 3
  },
  "output_files": {
    "matched_gpkg": "output/matched_traffic_lights.gpkg",
    "unmatched_gpkg": "output/output_2_unmatched.gpkg",
    "groups_dir": "output/groups",
    "report_txt": "output/report.txt"
  }
}
```

### Common CRS Codes

- `EPSG:4326` - WGS84 (Global, default)
- `EPSG:3857` - Web Mercator
- `EPSG:2180` - Poland (PUWG 1992)
- `EPSG:2965` - Poland (PUWG 2000)
- `EPSG:32633` - UTM Zone 33N

### Grouping Parameters

```json
"grouping": {
  "min_group_size": 50,      # Minimum objects per group
  "max_group_size": 70,      # Maximum objects per group
  "epsilon": 1000,           # DBSCAN radius (in CRS units)
  "min_samples": 3           # DBSCAN minimum samples
}
```

#### Optimization Tips

**For dense urban areas:**
```json
"epsilon": 500,
"max_group_size": 60
```

**For sparse rural areas:**
```json
"epsilon": 2000,
"max_group_size": 80
```

## Input Data Format

### CSV Format (traffic_lights.csv)

Minimum required columns:

```csv
id,latitude,longitude,intersection_id,street_name
1,52.2296,-0.1234,101,Main Street
2,52.2297,-0.1235,101,Main Street
3,52.2300,-0.1240,102,Second Street
```

Supported column names:
- **Latitude:** latitude, lat, y, Y
- **Longitude:** longitude, lon, x, X

### GPKG Files

**roads.gpkg:**
- Geometry: LineString
- Contains road network lines

**buffers.gpkg:**
- Geometry: Polygon
- Contains buffer zones for analysis

## Grouping Algorithm

### Stage 1: DBSCAN Clustering

Identifies natural geographic clusters:
- epsilon = 1000 (search radius in meters)
- min_samples = 3 (minimum points for cluster)

### Stage 2: Hierarchical Subdivision

Large clusters (> max_group_size) are recursively divided:
- Second DBSCAN pass with epsilon = 500
- Recursive subdivision until groups fit size constraints

### Stage 3: Intersection Integrity

Ensures all traffic lights from the same intersection_id stay in the same group.

## Usage

### Run the Processor

```bash
python traffic_lights_processor.py
```

### Output Files

```
output/
├── matched_traffic_lights.gpkg          # All matched traffic lights
├── output_2_unmatched.gpkg              # Unmatched traffic lights
├── groups/
│   ├── traffic_lights_group_000.gpkg
│   ├── traffic_lights_group_001.gpkg
│   └── ...
├── report.txt                           # Processing statistics
└── traffic_lights_YYYYMMDD_HHMMSS.log  # Detailed logs
```

### Programmatic Usage

```python
from traffic_lights_processor import TrafficLightsProcessor

processor = TrafficLightsProcessor('config.json')
processor.load_traffic_lights()
processor.load_roads()
processor.load_buffers()
processor.ensure_same_crs()
processor.select_intersected_roads()
processor.select_matched_traffic_lights()
processor.identify_unmatched_lights()

processor.group_lights_by_proximity(
    min_group_size=50,
    max_group_size=70,
    epsilon=1000,
    min_samples=3
)

processor.save_matched_lights()
processor.save_unmatched_lights()
processor.save_grouped_lights()
```

## Viewing Results

GPKG files can be viewed in:
- **QGIS** (free, recommended) - https://qgis.org/
- **ArcGIS**
- **FME**
- **GeoPandas** (Python)

### QGIS Quick Start

```bash
# Install QGIS
# Windows: Download from https://qgis.org/
# macOS: brew install qgis
# Linux: sudo apt-get install qgis

# Open GPKG file
# File → Open → traffic_lights_group_000.gpkg
```

## Troubleshooting

### Problem: "FileNotFoundError: config.json"

**Solution:** Ensure config.json is in the same directory as traffic_lights_processor.py

### Problem: "No such file" error when loading data

**Solution:** Check paths in config.json. Paths are relative to where the script is run.

### Problem: Too few traffic lights in groups

**Solution:** Increase `epsilon` in config.json

### Problem: Too many traffic lights in groups

**Solution:** Decrease `epsilon` or increase `max_group_size`

### Problem: GDAL/GeoPandas installation issues

**Windows:**
```bash
pip install --only-binary :all: geopandas
```

**macOS:**
```bash
brew install gdal
pip install geopandas
```

**Linux:**
```bash
sudo apt-get install gdal-bin libgdal-dev
pip install geopandas
```

## Performance

Estimated processing times for 5,000 traffic lights:

- Data loading: 1-5 seconds
- Geometric selection: 2-10 seconds
- DBSCAN clustering: 5-30 seconds
- Results export: 10-60 seconds

**Total: ~20-100 seconds**

## Logging

Detailed logs are written to:
- **File:** `traffic_lights_YYYYMMDD_HHMMSS.log`
- **Console:** Real-time output during processing

## License

MIT License - See LICENSE file

## Author

Kamil Lisek - TomTom

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues or questions:
- Open an issue on GitHub
- Contact: kamillisek@tomtom.com

## Changelog

### v1.0.0 (2026-06-16)

- Initial release
- Full DBSCAN clustering implementation
- Intelligent grouping algorithm
- Comprehensive documentation
- Ready for production use
