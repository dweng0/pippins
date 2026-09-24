# Infra

Terraform, one free-tier EC2 instance running the app via Docker Compose. State is local (fine for solo/throwaway use — an S3+DynamoDB backend is the real-world upgrade).

## First-time setup
```
cd infra
cp terraform.tfvars.example terraform.tfvars   # fill in the repo URL
terraform init
terraform plan
terraform apply
```

## Shell access: SSM, no SSH port
There is no inbound port 22. Access goes through AWS Systems Manager Session Manager: the instance role has `AmazonSSMManagedInstanceCore`, the agent (preinstalled on AL2023) connects outbound, and IAM decides who gets in. Your IP doesn't matter.

Local prerequisites: AWS CLI v2 plus the Session Manager plugin (`sudo dpkg -i session-manager-plugin.deb`, from the AWS docs "Install the Session Manager plugin"). Then:
```
aws ssm start-session --region eu-north-1 --target $(terraform output -raw instance_id)
```
For `ssh`/`scp` (still uses the key pair, tunnelled through SSM), add to `~/.ssh/config`:
```
Host stackcx
  HostName <instance_id from terraform output>
  User ec2-user
  IdentityFile ~/.ssh/stackcx-assessment.pem
  ProxyCommand sh -c "aws ssm start-session --region eu-north-1 --target %h --document-name AWS-StartSSHSession --parameters portNumber=%p"
```

## Web traffic: Cloudflare proxy only
Ports 80/443 accept only Cloudflare's edge ranges (fetched from `cloudflare.com/ips-v4` at plan time), so the DNS record must be **proxied** (orange cloud) and hitting the raw IP gets nothing. Cloudflare SSL mode is **Flexible** until the box has its own TLS listener (then Full (strict) with an origin cert). Django sees `X-Forwarded-Proto: https` from Cloudflare, so `DJANGO_HTTPS=true` works without redirect loops.

## Production `.env`
Then, one-time, create the box's production `.env` (gitignored, so `git pull` never brings it). Use generated secrets, not the dev values; see `.env.example` for the keys, and set `DJANGO_SETTINGS_MODULE=config.settings.prod`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, and `DJANGO_HTTPS` (false only while serving plain HTTP):
```
scp prod.env stackcx:/home/ec2-user/app/.env
ssh stackcx 'cd app && docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build'
```

## Ongoing deploys
Pull-based, no inbound SSH from CI. A systemd timer on the box (`stackcx-deploy.timer`, every 2 min) runs `deploy.sh`, which fetches `origin/main` and deploys it only if the `ci.yml` run for that exact commit concluded `success`. Push to `main`, CI passes, live within ~2 minutes. Logs: `journalctl -u stackcx-deploy.service`.

There is no inbound SSH at all, so CI can't push to the box; it pulls.

## Changing infra
`lifecycle.ignore_changes` covers `ami`: the AMI data source moves whenever Amazon publishes a new image, and a new AMI forces instance replacement, which would wipe Postgres on the root volume. Roll the AMI deliberately (`terraform apply -replace=aws_instance.app`) after backing up.

Infra changes (instance type, security group rules, etc.) go through `terraform plan` + `apply` by hand, not CI — deliberately not automated. Small blast radius here, but reading the plan diff before applying is a five-second habit worth keeping.

## Teardown
```
terraform destroy
```
Do this after the assessment call if you don't want the box running (though a single free-tier t3.micro costs nothing while under the 750hr/mo allowance anyway).
