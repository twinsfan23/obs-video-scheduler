@echo off
set TOMCAT_DIR=apache-tomcat-9.0.89

pushd %TOMCAT_DIR%
pushd bin

catalina.bat run
