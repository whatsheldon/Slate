import setuptools
from slate import __version__

with open('README.md', 'r') as file:
    long_description = file.read()

with open("requirements.txt") as file:
    install_requires = file.read().splitlines()


classifiers = [
    'Development Status :: 3 - Alpha',
    'Framework :: AsyncIO',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Natural Language :: English',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3 :: Only',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: Implementation :: CPython',
    'Topic :: Software Development',
    'Topic :: Software Development :: Libraries',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'Typing :: Typed'
]

project_urls = {
    'Documentation': 'https://github.com/Axelancerr/Slate',
    'Source': 'https://github.com/Axelancerr/Slate',
    'Issue Tracker': 'https://github.com/Axelancerr/Slate/issues',
}

setuptools.setup(
    name='Slate',
    version=__version__,
    description='A Lavalink and Andesite wrapper.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Axelancerr',
    author_email=None,
    url='https://github.com/Axelancerr/Slate',
    packages=['slate'],
    classifiers=classifiers,
    license='MIT',
    install_requires=install_requires,
    python_requires=">=3.8",
    project_urls=project_urls,
)
