# DodoBot deploy scripts

Intended for AWS free tier (`t3.micro` Amazon Linux 2023).

## Files

| File | Purpose |
|------|---------|
| `launch.ps1`        | PowerShell wrapper around the AWS CLI. Creates key pair, security group, launches the EC2 instance, injects `bootstrap.sh` as user-data. |
| `bootstrap.sh`      | Runs on the EC2 host on first boot (and is re-runnable). Installs Python 3.12, ffmpeg, clones the repo, sets up the venv, installs and enables the systemd service. |
| `dodobot.service`   | systemd unit; restarts on failure, locked-down privileges. |

## One-shot provision

```powershell
# from the repo root:
.\deploy\launch.ps1 -Region us-east-1 -RepoUrl https://github.com/DODOBots/DodoBot.git
```

Then upload your populated `.env`:

```powershell
scp -i .\deploy\dodobot-key.pem .\.env ec2-user@<public-ip>:/tmp/.env
ssh -i .\deploy\dodobot-key.pem ec2-user@<public-ip> `
    'sudo mv /tmp/.env /opt/dodobot/.env && sudo chown dodobot:dodobot /opt/dodobot/.env && sudo chmod 600 /opt/dodobot/.env && sudo systemctl restart dodobot'
```

## Logs

```
ssh -i .\deploy\dodobot-key.pem ec2-user@<public-ip> 'sudo journalctl -u dodobot -f'
```

## Free tier notes

- `t3.micro` = 750 h/month free for 12 months. One instance running 24/7 fits exactly.
- 30 GB `gp3` root volume is inside the 30 GB free tier (we request exactly 30).
- After the 12-month window: ~$7.50/month for `t3.micro`, or switch to `t4g.nano` (ARM Graviton) at ~$3/month by changing `-InstanceType t4g.nano` and using an `arm64` AMI filter.
