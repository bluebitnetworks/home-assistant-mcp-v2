from setuptools import setup, find_packages

setup(
    name="home-assistant-mcp",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "homeassistant-api>=4.0.0",
        "pyyaml>=6.0",
        "requests>=2.28.1",
        "aiohttp>=3.8.3",
        "jinja2>=3.1.2",
        "pytest>=7.2.0",
        "pytest-asyncio>=0.20.0",
        "pydantic>=1.10.5",
        "fastapi>=0.95.0",
        "uvicorn>=0.21.0",
        "python-dotenv>=1.0.0",
        "numpy>=1.24.0",
    ],
    python_requires=">=3.8",
)
