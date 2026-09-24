# Infra

Terraform, one free-tier EC2 instance running the app via Docker Compose. State is local (fine for solo/throwaway use — an S3+DynamoDB backend is the real-world upgrade).

## First-time setup
```
cd infra
cp terraform.tfvars.example terraform.tfvars   # fill in your IP + repo URL
terraform init
terraform plan
terraform apply
```

Then, one-time, create the box's production `.env` (gitignored, so `git pull` never brings it). Use generated secrets, not the dev values; see `.env.example` for the keys, and set `DJANGO_SETTINGS_MODULE=config.settings.prod`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, and `DJANGO_HTTPS` (false only while serving plain HTTP):
```
scp -i ~/.ssh/stackcx-assessment.pem prod.env ec2-user@$(terraform output -raw instance_public_ip):/home/ec2-user/app/.env
ssh -i ~/.ssh/stackcx-assessment.pem ec2-user@$(terraform output -raw instance_public_ip) \
  'cd app && docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build'
```

## Ongoing deploys
Pull-based, no inbound SSH from CI. A systemd timer on the box (`stackcx-deploy.timer`, every 2 min) runs `deploy.sh`, which fetches `origin/main` and deploys it only if the `ci.yml` run for that exact commit concluded `success`. Push to `main`, CI passes, live within ~2 minutes. Logs: `journalctl -u stackcx-deploy.service`.

SSH is restricted to one IP (`allowed_ssh_cidr`), which is why CI can't push to the box. If your IP changes, update `terraform.tfvars` and `terraform apply`.

## Changing infra
Infra changes (instance type, security group rules, etc.) go through `terraform plan` + `apply` by hand, not CI — deliberately not automated. Small blast radius here, but reading the plan diff before applying is a five-second habit worth keeping.

## Teardown
```
terraform destroy
```
Do this after the assessment call if you don't want the box running (though a single free-tier t3.micro costs nothing while under the 750hr/mo allowance anyway).
