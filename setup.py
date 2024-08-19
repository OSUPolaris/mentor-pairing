from setuptools import setup

requirements = [
    "pandas",
    "numpy"
]

requirements_dev = ["pytest"]

setup(
    name="stablepairing",
    version="0.1.0",
    description="Stable pairing algorithm for mentoring programs",
    url="https://github.com/OSUPolaris/mentor-pairing",
    author="OSU Polaris Program",
    packages=["stablepairing"],
    package_dir={"": "src"},
    install_requirements=requirements,
    extras_require={
        "dev": requirements_dev
    },
    scripts=["bin/mentorship_pairing", "bin/speednetwork_pairing"]
)
