@ECHO OFF 

set OSGEO4W_ROOT=C:\Program Files\QGIS 3.30.1

set PATH=%OSGEO4W_ROOT%\bin;%PATH%
set PATH=%PATH%;%OSGEO4W_ROOT%\apps\qgis\bin

@echo off
call "%OSGEO4W_ROOT%\bin\o4w_env.bat"
@echo off
path %OSGEO4W_ROOT%\apps\qgis\bin;%PATH%

cd /d %~dp0