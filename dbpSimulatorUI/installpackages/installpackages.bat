@echo ON

cd /d %~dp0

call "py3-env.bat"

python3.exe -m pip install --upgrade pip
python3 -m pip install --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --trusted-host pypi.org -r requirements.txt