:: Install dependencies
if %USE_CONDA% == yes (
    conda install -q -y -c spyder-ide --file requirements/conda.txt
    conda install -q -y -c spyder-ide --file requirements/tests.txt
) else (
    :: Update pip and setuptools
    pip install -U pip setuptools

    :: Install Spyder and its dependencies from our setup.py
    pip install -e .[test]

    :: Install qtpy from Github
    pip install git+https://github.com/spyder-ide/qtpy.git

    :: Install qtconsole from Github
    pip install git+https://github.com/jupyter/qtconsole.git
)

:: The newly introduced changes to the Python packages in Anaconda
:: are breaking our tests. Reverting to known working builds.
::if %PYTHON_VERSION% == 2.7 (
::    conda install -q -y python=2.7.15=hcb6e200_5
::) else if %PYTHON_VERSION% == 3.6 (
::    conda install -q -y python=3.6.8=h9f7ef89_0
::)

:: Install spyder-kernels from master
pip install -q --no-deps git+https://github.com/spyder-ide/spyder-kernels

:: Install codecov
pip install -q codecov
