resource "random_password" "db" {
  length  = 30
  special = false
}

resource "aws_db_subnet_group" "postgres" {
  name       = "${local.name}-db-subnets"
  subnet_ids = aws_subnet.private_data[*].id
}

resource "aws_db_instance" "postgres" {
  identifier                = "${local.name}-postgres"
  engine                    = "postgres"
  engine_version            = "16.3"
  instance_class            = "db.r7g.large"
  allocated_storage         = 200
  max_allocated_storage     = 2000
  storage_encrypted         = true
  kms_key_id                = aws_kms_key.main.arn
  username                  = "rautrex_app"
  password                  = random_password.db.result
  db_name                   = "rautrex"
  publicly_accessible       = false
  multi_az                  = true
  db_subnet_group_name      = aws_db_subnet_group.postgres.name
  vpc_security_group_ids    = [aws_security_group.rds_sg.id]
  backup_retention_period   = 35
  deletion_protection       = true
  skip_final_snapshot       = false
  final_snapshot_identifier = "${local.name}-final-snapshot"
}

