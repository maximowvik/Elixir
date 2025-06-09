@echo off

echo "Removing old build and dist directories"
rmdir /S /Q main.dist
rmdir /S /Q main.build

echo "Create virtual environment"
py -m venv .venv

echo "Start virtual environment"
call .venv\Scripts\activate.bat

echo "Update library and plugins"
py -m pip install --upgrade pip setuptools

echo "Installation library and plugins"
py -m pip install -r requirements.txt

echo "Start build project"
python -m nuitka --standalone --lto=yes --windows-icon-from-ico=d:\projects\Elixir\vendor\icon\logonew.ico --enable-plugin=pyqt6 --include-data-dir=vendor=vendor --include-data-dir=pic=pic --include-data-dir=images=images --include-data-dir=icon=icon --module-parameter=torch-disable-jit=yes main.py

echo "Copy necessary folders to main.dist"
xcopy /E /I vendor main.dist\vendor
xcopy /E /I pic main.dist\pic
xcopy /E /I images main.dist\images
xcopy /E /I icon main.dist\icon

echo "Build completed"
