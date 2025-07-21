from setuptools import setup, find_packages

setup(
    name="bboxanntool",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.26.0,<2.0.0",
        "PyQt5>=5.15.9,<5.16.0",
        "opencv-python-headless>=4.9.0,<4.10.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0,<8.0.0",
            "pytest-qt>=4.5.0",
        ],
    },
    entry_points={
        'console_scripts': [
            'bboxanntool=bboxanntool.app:main',
        ],
    },
    author="cm107",
    description="A GUI tool for annotating bounding boxes in images",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Environment :: X11 Applications :: Qt",
        "Topic :: Scientific/Engineering :: Image Recognition",
    ],
    python_requires=">=3.7",
)