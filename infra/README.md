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

Then, one-time, copy `.env` up (it's gitignored, so `git pull` on the box never gets it):
```
scp -i ~/.ssh/stackcx-assessment.pem ../.env ec2-user@$(terraform output -raw instance_public_ip):/home/ec2-user/app/.env
ssh -i ~/.ssh/stackcx-assessment.pem ec2-user@$(terraform output -raw instance_public_ip) \
  'cd app && docker-compose up -d --build'
```

## Ongoing deploys
Handled by `.github/workflows/deploy.yml` — push to `main`, CI runs tests, on success it SSHes in, `git pull`s, restarts the stack. Needs two repo secrets set (Settings → Secrets → Actions):
- `EC2_HOST` — the Elastic IP from `terraform output instance_public_ip`
- `EC2_SSH_KEY` — contents of `~/.ssh/stackcx-assessment.pem`

## Changing infra
Infra changes (instance type, security group rules, etc.) go through `terraform plan` + `apply` by hand, not CI — deliberately not automated. Small blast radius here, but reading the plan diff before applying is a five-second habit worth keeping.

## Teardown
```
terraform destroy
```
Do this after the assessment call if you don't want the box running (though a single free-tier t3.micro costs nothing while under the 750hr/mo allowance anyway).
