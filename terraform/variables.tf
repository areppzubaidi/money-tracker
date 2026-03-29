variable "aws_region" {
  description = "AWS region"
  default     = "ap-southeast-1"
}

variable "instance_type" {
  description = "EC2 instance type (free tier)"
  default     = "t2.micro"
}

variable "ami_id" {
  description = "Ubuntu 22.04 LTS AMI ID for ap-southeast-1"
  default     = "ami-0659642169bf1b4b2"  # Replace with actual ID for ap-southeast-1
}

variable "key_name" {
  description = "Name of the existing key pair"
  default     = "devops-key"
}
