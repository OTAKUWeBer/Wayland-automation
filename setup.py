from setuptools import setup, find_packages

setup(
    name="wayland_automation",
    version="0.1.4",
    description="A tool for automating Wayland tasks using system packages wtype and wayland-info",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="OTAKUWeBer",
    author_email="rtweber2004@gmail.com",
    url="https://github.com/OTAKUWeBer/Wayland-automation",
    packages=find_packages(),
    install_requires=[
        # Add any additional Python dependencies here.
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
    ],
    entry_points={
        "console_scripts": [
            "wayland-automation=wayland_automation.__main__:main",
        ]
    },
    python_requires=">=3.6",
)
