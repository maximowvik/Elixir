<# Удаление старых директорий сборки и виртуальной среды #>
Write-Host "Removing old build and dist directories"
Remove-Item -Path "main.build" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "main.dist" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path ".venv" -Recurse -Force -ErrorAction SilentlyContinue

<# Создание директории для сборки приложения #>
$outputDir = "AppOutput"
New-Item -ItemType Directory -Path $outputDir -Force

<# Создание виртуальной среды #>
Write-Host "Creating virtual environment"
python -m venv .venv

<# Активация виртуальной среды #>
Write-Host "Activating virtual environment"
.\.venv\Scripts\Activate.ps1

<# Обновление pip и setuptools #>
Write-Host "Updating pip and setuptools"
python -m pip install --upgrade pip setuptools

<# Установка зависимостей #>
Write-Host "Installing dependencies"
python -m pip install -r requirements.txt

<# Сборка проекта с использованием Nuitka #>
Write-Host "Building the project with Nuitka"
python -m nuitka --standalone --show-progress --lto=yes --windows-icon-from-ico=d:\projects\Elixir\vendor\icon\logonew.ico --enable-plugin=pyqt6 --include-data-dir=vendor=vendor --include-data-dir=pic=pic --include-data-dir=images=images --include-data-dir=icon=icon --output-dir=$outputDir main.py

<# Копирование необходимых папок в директорию сборки #>
Write-Host "Copying necessary folders to the output directory"
Copy-Item -Path "vendor" -Destination "$outputDir\vendor" -Recurse -Force
Copy-Item -Path "pic" -Destination "$outputDir\pic" -Recurse -Force
Copy-Item -Path "images" -Destination "$outputDir\images" -Recurse -Force
Copy-Item -Path "icon" -Destination "$outputDir\icon" -Recurse -Force

Write-Host "Build completed"
