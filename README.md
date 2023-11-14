# isar-exr

Integration and Supervisory control of Autonomous ground Robots - exr

The abbreviation "exr" stands for ExRobotics, the maker of the [ExR-2](https://exrobotics.global/robots/exr-2) robot, which this package is intended for.

Technically speaking, this package integrates to the API of [Energy Robotics](https://www.energy-robotics.com/), the provider of a cloud-based platform to control fleets of robots from multiple vendors including ExRobotics.

## Authentication

You need to have a user account on the Energy Robotics login portal which lets you create an API key.
For authentication the email address of this user account is used as user name and the API key as password.

### Contributing

We welcome all kinds of contributions, including code, bug reports, issues, feature requests, and documentation. The
preferred way of submitting a contribution is to either make an [issue](https://github.com/equinor/isar-exr/issues) on
GitHub or by forking the project on GitHub and making a pull requests.

## Installation

Clone and install in the repository root folder.

```
git clone https://github.com/equinor/isar_exr
cd isar_exr
pip install -e ".[dev]"
```

Set the following environment variables (alternatively in a .env file like `.env.example`):

```bash
export EXR_ROBOT_API_USERNAME = "email-here"
export EXR_ROBOT_API_PASSWORD = "api-key-here"
export EXR_API_URL = "ADD URL HERE"
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
