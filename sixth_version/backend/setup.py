from setuptools import setup, find_packages

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='core_ai_backend',
    version='0.1.0',
    author='Core AI',
    author_email='author@example.com',
    description='Backend for the Core AI application',
    long_description=open('README.md').read() if open('README.md') else '',
    long_description_content_type='text/markdown',
    url='https://github.com/pypa/sampleproject',
    packages=find_packages(),
    install_requires=required,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
) 