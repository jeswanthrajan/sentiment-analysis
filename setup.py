from setuptools import setup, find_packages

setup(
    name="sentimentscope",
    version="0.1.0",
    author="Me",
    author_email="me@example.com",
    description="Simple sentiment analysis tool",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "flask",
        "pandas",
        "sqlalchemy",
        "python-dotenv",
    ],
)
