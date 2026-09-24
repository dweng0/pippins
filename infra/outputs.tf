output "instance_public_ip" {
  value = aws_eip.app.public_ip
}

output "instance_id" {
  value = aws_instance.app.id
}

output "ssm_command" {
  value = "aws ssm start-session --region ${var.aws_region} --target ${aws_instance.app.id}"
}
