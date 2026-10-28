from setuptools import setup, find_packages

setup(
    name="wayland_automation",
    version="0.3.0",
    description="A tool for automating Wayland tasks using system packages wtype and wayland-info",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="OTAKUWeBer",
    author_email="rtweber2004@gmail.com",
    url="https://github.com/OTAKUWeBer/Wayland-automation",
    packages=find_packages(),
    package_data={
        "wayland_automation": ["*.js"],
    },
    include_package_data=True,
    install_requires=[
        "evdev",
    ],
    extras_require={
        "kde": ["dbus-next"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
    ],
    entry_points={
        "console_scripts": [
            "wayland-automation=wayland_automation.__main__:main",
        ]
    },
    python_requires=">=3.8",
)
