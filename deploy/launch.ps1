<#
.SYNOPSIS
  Provisions a t3.micro (free tier) EC2 instance running DodoBot in us-east-1.

.DESCRIPTION
  Idempotent helper around `aws ec2 ...` commands:
    1. Creates key pair    (if missing) - saved as deploy\<KeyName>.pem
    2. Creates SG          (if missing) - ingress: SSH 22/tcp from current public IP only
    3. Looks up the latest Amazon Linux 2023 AMI
    4. Runs a t3.micro with deploy\bootstrap.sh as user-data
    5. Prints the public IP + next-step commands

.PARAMETER Region
  AWS region. Default: us-east-1.

.PARAMETER KeyName
  EC2 key pair name. Default: dodobot-key.

.PARAMETER SgName
  Security group name. Default: dodobot-sg.

.PARAMETER RepoUrl
  Git URL the bootstrap script will clone.

.PARAMETER Branch
  Branch to deploy. Default: main.

.EXAMPLE
  .\deploy\launch.ps1 -RepoUrl https://github.com/DODOBots/DodoBot.git
#>
[CmdletBinding()]
param(
    [string] $Region = "us-east-1",
    [string] $KeyName = "dodobot-key",
    [string] $SgName = "dodobot-sg",
    [string] $RepoUrl = "https://github.com/ZizhaoZheng-Charlie/DodoBotOffical.git",
    [string] $Branch = "main",
    [string] $InstanceType = "t3.micro"
)

$ErrorActionPreference = "Continue"
$PSNativeCommandUseErrorActionPreference = $false
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$pemPath = Join-Path $here "$KeyName.pem"

function Test-AwsCmd {
    param([Parameter(ValueFromRemainingArguments)] $Args)
    & aws @Args --region $Region --output json 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}

Write-Host "Region: $Region  Key: $KeyName  SG: $SgName" -ForegroundColor Cyan

# -------- 1. Key pair --------
if (Test-AwsCmd ec2 describe-key-pairs --key-names $KeyName) {
    Write-Host "Key pair $KeyName already exists (assuming PEM at $pemPath)"
} else {
    Write-Host "Creating key pair $KeyName" -ForegroundColor Green
    # Use JSON output + ConvertFrom-Json so embedded \n newlines survive exactly.
    $kpJson = (& aws ec2 create-key-pair --key-name $KeyName --region $Region --output json)
    if ($LASTEXITCODE -ne 0) { throw "create-key-pair failed" }
    $material = ($kpJson | ConvertFrom-Json).KeyMaterial
    [System.IO.File]::WriteAllText($pemPath, $material, [System.Text.Encoding]::ASCII)
    icacls $pemPath /inheritance:r | Out-Null
    icacls $pemPath /grant:r "$($env:USERNAME):(R)" | Out-Null
    Write-Host "Saved PEM to $pemPath" -ForegroundColor Green
}

# -------- 2. Security group --------
$sgId = $null
if (Test-AwsCmd ec2 describe-security-groups --group-names $SgName) {
    $sgId = (& aws ec2 describe-security-groups --group-names $SgName --region $Region --query 'SecurityGroups[0].GroupId' --output text)
    Write-Host "Security group exists: $sgId"
} else {
    Write-Host "Creating security group $SgName" -ForegroundColor Green
    $sgId = (& aws ec2 create-security-group --group-name $SgName `
        --description "DodoBot SSH access" --region $Region --query GroupId --output text)
    if ($LASTEXITCODE -ne 0) { throw "create-security-group failed" }

    $myIp = (Invoke-RestMethod -Uri "https://checkip.amazonaws.com").Trim()
    Write-Host "Allowing SSH from $myIp/32" -ForegroundColor Green
    & aws ec2 authorize-security-group-ingress --group-id $sgId `
        --protocol tcp --port 22 --cidr "$myIp/32" --region $Region | Out-Null
}

# -------- 3. Latest Amazon Linux 2023 AMI --------
$amiId = (aws ec2 describe-images `
    --owners amazon `
    --filters "Name=name,Values=al2023-ami-2023.*-x86_64" "Name=state,Values=available" `
    --query "sort_by(Images, &CreationDate)[-1].ImageId" `
    --output text --region $Region)
Write-Host "AMI: $amiId"

# -------- 4. Launch --------
$bootstrap = Get-Content -Raw (Join-Path $here "bootstrap.sh")
# Inject REPO_URL/BRANCH by prepending env lines. `bootstrap.sh` already honors them.
$userData = "#!/bin/bash`nexport REPO_URL='$RepoUrl'`nexport BRANCH='$Branch'`n" + $bootstrap
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($userData))

Write-Host "Launching $InstanceType ..." -ForegroundColor Green
$instanceId = (aws ec2 run-instances `
    --region $Region `
    --image-id $amiId `
    --instance-type $InstanceType `
    --key-name $KeyName `
    --security-group-ids $sgId `
    --user-data $b64 `
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=dodobot}]' `
    --block-device-mappings 'DeviceName=/dev/xvda,Ebs={VolumeSize=30,VolumeType=gp3,DeleteOnTermination=true}' `
    --query 'Instances[0].InstanceId' --output text)

Write-Host "Instance: $instanceId - waiting for running state" -ForegroundColor Green
aws ec2 wait instance-running --instance-ids $instanceId --region $Region

$publicIp = (aws ec2 describe-instances --instance-ids $instanceId --region $Region `
    --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

Write-Host ""
Write-Host "=============================================================" -ForegroundColor Cyan
Write-Host " Instance running at $publicIp (id $instanceId)" -ForegroundColor Cyan
Write-Host " Bootstrap runs in background. Watch it:"
Write-Host "   ssh -i $pemPath ec2-user@$publicIp 'sudo tail -f /var/log/cloud-init-output.log'"
Write-Host ""
Write-Host " Upload your .env:"
Write-Host "   scp -i $pemPath .env ec2-user@${publicIp}:/tmp/.env"
Write-Host "   ssh -i $pemPath ec2-user@$publicIp 'sudo mv /tmp/.env /opt/dodobot/.env && sudo chown dodobot:dodobot /opt/dodobot/.env && sudo chmod 600 /opt/dodobot/.env && sudo systemctl restart dodobot'"
Write-Host ""
Write-Host " Tail the bot:"
Write-Host "   ssh -i $pemPath ec2-user@$publicIp 'sudo journalctl -u dodobot -f'"
Write-Host "=============================================================" -ForegroundColor Cyan
