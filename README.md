# dbpRisk 2.0 - QGIS Plugin

[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](LICENSE)

## Overview

dbpRisk 2.0 is a QGIS plugin designed to simulate and assess the formation of disinfection by-products (DBPs) in drinking water distribution networks. It performs simulation experiments using EPANET-MSX files to model chemical reactions under various conditions and uncertainties. The plugin enables users to evaluate how different parameters influence DBP formation, offering insight into water quality dynamics.

By integrating these simulations into the QGIS environment, dbpRisk 2.0 allows for spatially-informed risk analysis, helping decision-makers and researchers visualize, predict, and manage DBP-related risks more effectively.

## Features

- **EPANET Integration**: Load and simulate EPANET-MSX water network models
- **DBP Risk Assessment**: Analyze disinfection by-product formation
- **Spatial Visualization**: Visualize simulation results on QGIS maps
- **Uncertainty Analysis**: Evaluate parameter uncertainties
- **Time Series Analysis**: Monitor DBP levels over time

## Requirements

- QGIS >= 3.30
- Python 3.x
- Required Python packages:
  - numpy==1.22.4
  - epyt==1.2.2
  - matplotlib==3.7.2
  - xlsxwriter>=3.2.0
  - openpyxl>=3.1.0
  - pandas>=1.5.3

## Installation

### From QGIS Plugin Repository (Recommended)

1. Open QGIS
2. Go to `Plugins` → `Manage and Install Plugins`
3. Search for "dbpRisk 2.0"
4. Click `Install Plugin`

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/KIOS-Research/dbpSimulatorUI/releases)
2. Extract the ZIP file
3. Copy the `dbpRisk2` folder to your QGIS plugins directory:
   - **Linux**: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - **Windows**: `C:\Users\<username>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`
   - **macOS**: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
4. Restart QGIS
5. Enable the plugin from `Plugins` → `Manage and Install Plugins`

### Installing Dependencies

Dependencies are automatically installed when you first run the plugin. If you need to manually install them:

**Linux/macOS:**
```bash
cd dbpSimulatorUI/installpackages
./installpackages.sh
```

**Windows:**
```cmd
cd dbpSimulatorUI\installpackages
installpackages.bat
```

## Usage

1. Open QGIS
2. Enable the plugin from the plugins menu
3. Click on the dbpRisk 2.0 toolbar icon
4. Load your EPANET & MSX model files
5. Configure simulation parameters
6. Run the simulation
7. Visualize results on the map

For detailed usage instructions, please refer to the [documentation](https://dbprisk2.readthedocs.io/en/latest/manual.html#installation-instructions).

## Contributing

If you want to contribute, please check out our [Code of Conduct](CODE_OF_CONDUCT.md). Conduct. Everyone is welcome to contribute whether reporting a new issue, suggesting a new feature, or writing code. If you want to contribute code, you can create a new fork in the repo to your own account. Make your commits on your dev branch (based on dev) and when you are finished then you can create a pull request to test the code and discuss your changes.

## License

GPL LICENSE v3.0. See the [LICENSE](LICENSE) file for details.

## Authors

Dimitris Papazachariou, Ioannis Chrysostomou, Andreas Demosthenous, Costas Papadopoulos, Pavlos Pavlou, Marios Kyriakou, Stelios Vrachimis, Demetris Eliades
<br>**KIOS Research and Innovation Center of Excellence, University of Cyprus**

## Contact

For questions, issues, or support:
- Email: kiriakou.marios@ucy.ac.cy
- Issues: https://github.com/KIOS-Research/dbpRisk2/issues

## Acknowledgments

- We created this plugin for the [IntoDBP project](https://intodbp.eu/).
- Members of the IntoDBP project provided feedback.

## Citation



