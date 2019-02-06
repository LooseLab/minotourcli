# minotourcli

1. Create virtual environment 

```bash
python -m venv [Path_To_Virtual_Environment_Directory]
```

2. Add Environment to PYTHONPATH environment variable
```bash
export PYTHONPATH=$PYTHONPATH:/[Path_To_Virtual_Environment_Directory]
```

3. Install using setup.py
```bash
python setup.py install develop --install-dir [Path_To_Virtual_Environment_Directory]
```


