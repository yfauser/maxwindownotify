from setuptools import setup
import io

def read(*filenames, **kwargs):
    encoding = kwargs.get('encoding', 'utf-8')
    sep = kwargs.get('sep', '\n')
    buf = []
    for filename in filenames:
        with io.open(filename, encoding=encoding) as f:
            buf.append(f.read())
    return sep.join(buf)

long_description = read('README.rst')

setup(
    name='maxwindownotify',
    version='1.1',
    packages=['maxwindownotify'],
    package_data={'maxwindownotify':['*'], 'maxwindownotify':['notifier_modules/*']},
    url='http://github.com/yfauser/maxwindownotify',
    license='MIT',
    author='yfauser',
    author_email='yfauser@yahoo.de',
    description='This little script (daemon) will poll for the status of all window sensors known to a MAX Cube system and check for open windows',
    long_description=long_description,
    classifiers=[
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: End Users/Desktop',
    'Topic :: Utilities',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 2.7'],
    install_requires=['requests>=2.7.0', 'netaddr>=0.7.18'],
    entry_points={
        'console_scripts': ['maxwindownotify = maxwindownotify.maxwindownotify:main']
    }
)
