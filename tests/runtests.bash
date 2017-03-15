#! /bin/bash

echo "Running python 2.7 tests first"

rm -rf venv | true

virtualenv -p python2.7 venv
source venv/bin/activate

pip install -e ../

python manage.py test

# Check that the test passed or failed
rc=$?

if [[ $rc != 0 ]]; then 
   echo "The python 2.7 tests failed"
   exit $rc 
fi

echo "The python 2.7 tests passed - trying on python 3"

rm -rf venv | true

virtualenv -p python3 venv
source venv/bin/activate

pip install -e ../

python manage.py test

# Check that the test passed or failed
rc=$?

if [[ $rc != 0 ]]; then 
   echo "The python 3 tests failed"
   exit $rc 
fi