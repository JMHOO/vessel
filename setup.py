from setuptools import setup

setup(name='vessel',
      version='0.0.1',
      description='A package for manipulate DICOM files',
      url='https://github.com/JMHOO/vessel',
      author='Jimmy Hu',
      author_email='huj22@uw.edu',
      license='MIT',
      packages=['vessel'],
      install_requires=[
          'pydicom', 'pillow', 'numpy'
      ],
      zip_safe=False)