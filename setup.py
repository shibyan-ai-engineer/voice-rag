from setuptools import setup, find_packages

# This setup.py exists for compatibility with pip install -e .
# Use poetry for actual dependency management.

setup(
    name="voice-rag",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.12,<3.13",
    install_requires=[
        "fastapi>=0.115.0",
        "uvicorn>=0.23.0",
        "python-multipart>=0.0.6",
        "kokoro>=0.9.4",
        "nemo-toolkit>=2.3.0",
        "langchain-core>=0.3.60",
        "langchain-community>=0.3.24",
        "faiss-cpu>=1.11.0",
        "soundfile>=0.13.1",
        "sounddevice>=0.5.2",
        "pypdf2>=3.0.1",
        "scikit-learn>=1.6.1",
        "langchain-ollama>=0.3.3",
        "websockets>=15.0.1",
    ],
)
