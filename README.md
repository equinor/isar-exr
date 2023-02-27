# isar-exr
Integration and Supervisory control of Autonomous ground Robots - exr

exr is an abbrivation of ExRobotics, which has made the robot [ExRobotics2(exr2)](https://exrobotics.global/robots/exr-2) which this package is intended for.

Technically speaking, this package integrates toward [EnergyRobotics'](https://www.energy-robotics.com/) API, which again communicates with the exr2 robot.

## Installation

Clone and install in the repository root folder.

```
git clone https://github.com/equinor/isar_exr
cd isar_exr
pip install -e ".[dev]"
```

Set the following environment variables (alternatively in a .env file):

```bash
export API_USERNAME = 
export API_PASSWORD = 
```

For development, it is recommended to install the lastest version of ISAR from [GitHub](https://github.com/equinor/isar) locally.
To install ISAR in the same environment from a local folder:

```bash
pip install -e path/to/local/isar/folder
```

Note that this installation might require [wheel](https://pypi.org/project/wheel/).

Finally, verify that you can run the tests:

```bash
pytest .
```
