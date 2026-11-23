# Resilient Infrastructure as Code Configuration
# Balanced ASG max_size connection surge matched with production memory-optimized RDS class
resource "aws_autoscaling_group" "web_asg" {
  name             = "prod-web-asg"
  min_size         = 2
  max_size         = 6
  desired_capacity = 2
}

resource "aws_db_instance" "postgres" {
  name           = "prod-primary-rds"
  instance_class = "db.r6g.large"
  engine         = "postgres"
}
