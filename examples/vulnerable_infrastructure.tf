# Vulnerable Infrastructure as Code Configuration
# Demonstrates ASG max_size connection surge vs under-provisioned RDS instance class
resource "aws_autoscaling_group" "web_asg" {
  name             = "prod-web-asg"
  min_size         = 4
  max_size         = 28
  desired_capacity = 4
}

resource "aws_db_instance" "postgres" {
  name           = "prod-primary-rds"
  instance_class = "db.t3.medium"
  engine         = "postgres"
}
