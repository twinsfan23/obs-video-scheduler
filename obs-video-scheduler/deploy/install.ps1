$ErrorActionPreference = "Stop"

Write-Host "Checking java installation..."

if ((-not (Test-Path env:JRE_HOME)) -and (-not (Test-Path env:JAVA_HOME))) {
  Write-Host "There's no JRE_HOME or JAVA_HOME set!"
  Write-Host "Install JDK or JRE and set JAVA_HOME or JRE_HOME appropriately"
  exit 1
}

$javaHome = $env:JRE_HOME
$javaBin = "bin\\java.exe"
if (-not $javaHome) {
  $javaHome = $env:JAVA_HOME
  Write-Host "JRE_HOME is not set, but found JAVA_HOME at $javaHome"
} else {
  Write-Host "Found JRE_HOME at $javaHome"
}

if (-not (Test-Path "$javaHome\\$javaBin")) {
  Write-Host "There's no $javaHome\\$javaBin"
  Write-Host "Fix your java installation"
  exit 1
}

Write-Host "Found $javaHome\\$javaBin"
Invoke-Expression "& '$javaHome\\$javaBin' --version"

Write-Host "Checking ffmpeg installation..."
try {
  Invoke-Expression "ffmpeg -version"
} catch {
  Write-Host "There's no ffmpeg"
  Write-Host "Download ffmpeg and add it to your PATH"
  exit 1
}

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'

$tomcatVersion = "9.0.89"
$tomcatArchive = "apache-tomcat-$tomcatVersion-windows-x64.zip"
$tomcatFolder = "apache-tomcat-$tomcatVersion"
$tomcatUrl = "https://archive.apache.org/dist/tomcat/tomcat-9/v$tomcatVersion/bin/$tomcatArchive"

$repo = "pashkal/obs-video-scheduler"
$schedulerAssetName = "obs-video-scheduler.zip"
$latestReleaseApi = "https://api.github.com/repos/$repo/releases/latest"

function Get-LatestSchedulerUrl {
  Write-Host "Looking up latest scheduler release..."
  $releaseInfo = Invoke-RestMethod -Uri $latestReleaseApi -Headers @{"User-Agent" = "obs-video-scheduler-installer"}
  $asset = $releaseInfo.assets | Where-Object { $_.name -eq $schedulerAssetName }
  if (-not $asset) {
    throw "Could not find $schedulerAssetName in latest release assets"
  }
  return $asset.browser_download_url
}

Write-Host "Downloading Tomcat $tomcatVersion..."
Invoke-WebRequest -Uri $tomcatUrl -Outfile "tomcat.zip"
Write-Host "Unpacking Tomcat..."
Expand-Archive -DestinationPath "." "tomcat.zip" -Force
Remove-Item tomcat.zip

Write-Host "Downloading scheduler (latest release)..."
$schedulerUrl = Get-LatestSchedulerUrl
Invoke-WebRequest -Uri $schedulerUrl -Outfile "scheduler.zip"
Write-Host "Unpacking scheduler..."
Expand-Archive -DestinationPath "." "scheduler.zip" -Force
Remove-Item scheduler.zip

Write-Host "Setting up web app..."
if (Test-Path "$tomcatFolder\\webapps") {
  Remove-Item -Recurse -Force "$tomcatFolder\\webapps"
}
New-Item "$tomcatFolder\\webapps" -ItemType directory -Force | Out-Null
Move-Item -Path ROOT.war -Destination "$tomcatFolder\\webapps\\ROOT.war" -Force

Write-Host "Setting up schedules dir..."
New-Item "data" -ItemType directory -Force | Out-Null
New-Item "data\\schedules" -ItemType directory -Force | Out-Null

Write-Host "Installation complete. Use run.bat to start Tomcat."
