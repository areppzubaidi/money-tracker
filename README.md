
# Money Tracker DevOps Project

## 📋 Table of Contents
- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Containerization with Docker](#containerization-with-docker)
- [Infrastructure as Code (Terraform)](#infrastructure-as-code-terraform)
- [Configuration Management (Ansible)](#configuration-management-ansible)
- [Deployment Walkthrough](#deployment-walkthrough)
- [Screenshots](#screenshots)
- [Troubleshooting & Common Issues](#troubleshooting--common-issues)
- [Clean Up](#clean-up)
- [Next Steps](#next-steps)

---

<img width="1408" height="768" alt="Gemini_Generated_Image_3fm0xl3fm0xl3fm0" src="https://github.com/user-attachments/assets/e3545b9a-1cf4-4ffb-8eb3-02f03de3a030" />

## Project Overview
The Money Tracker is a simple web application that allows users to add and view financial transactions. It consists of a static frontend (HTML/CSS) and a Python Flask backend with an in‑memory store. The project demonstrates a complete DevOps pipeline:

- Local development with virtual environment
- Containerization using Docker (multi‑arch)
- Infrastructure provisioning with Terraform (AWS EC2)
- Configuration management with Ansible (Docker, NGINX, app deployment)
- Manual CI/CD via Docker Hub

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Browser                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              AWS EC2 (Ubuntu 22.04, t2.micro)               │
│                                                             │
│  ┌─────────────┐      ┌──────────────────────────────┐    │
│  │   NGINX     │ ──► │   Docker Container            │    │
│  │ (port 80)   │      │   (Flask app, port 5000)    │    │
│  └─────────────┘      └──────────────────────────────┘    │
│         │                                                  │
│         ▼                                                  │
│  /var/www/html/                                            │
│  (static frontend files)                                   │
└─────────────────────────────────────────────────────────────┘
```

- **NGINX** serves static frontend files and proxies `/api/` requests to the Flask container.
- **Flask** runs inside a Docker container, listening on port 5000.
- **Frontend** is copied to `/var/www/html` during Ansible playbook execution.

---

## Prerequisites
- AWS account (Free Tier eligible)
- AWS CLI configured (`aws configure`)
- Terraform (≥ v1.0)
- Ansible (≥ 2.9)
- Docker Desktop (with Buildx support)
- Python 3.10+ and `pip`
- Git
- SSH key pair (created in AWS or locally)

---

## Local Development

### 1. Clone the repository
```bash
git clone https://github.com/your-username/money-tracker.git
cd money-tracker
```

### 2. Set up Python virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r backend/requirements.txt
```

### 4. Run the Flask backend (port 5001 – avoid macOS AirPlay conflict)
```bash
cd backend
python app.py
```
*The app runs on port 5001 by default (see `app.py`).*

### 5. Serve frontend (separate terminal)
```bash
cd frontend
python -m http.server 8000
```

### 6. Open browser at `http://localhost:8000`
Add a transaction to verify the API works.

---

## Containerization with Docker

### 1. Create `docker/Dockerfile`
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY frontend /app/static

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

### 2. Build multi‑arch image (for both AMD64 and ARM64)
```bash
docker buildx create --name multiarch --use
docker buildx build --platform linux/amd64,linux/arm64 -t your-dockerhub-username/money-tracker:latest --push -f docker/Dockerfile .
```
*Replace `your-dockerhub-username` with your Docker Hub username.*

### 3. Test locally (optional)
```bash
docker run -d -p 5002:5000 --name money-tracker your-dockerhub-username/money-tracker:latest
curl http://localhost:5002/api/transactions
```

---

## Infrastructure as Code (Terraform)

### 1. Terraform files (`terraform/`)

**variables.tf**
```hcl
variable "aws_region" {
  default = "ap-southeast-1"
}
variable "instance_type" {
  default = "t2.micro"
}
variable "ami_id" {
  # Replace with the latest Ubuntu 22.04 AMI for ap-southeast-1
  default = "ami-0659642169bf1b4b2"
}
variable "key_name" {
  default = "my-key"   # Your EC2 key pair name
}
```

**main.tf**
```hcl
provider "aws" {
  region = var.aws_region
}

resource "aws_security_group" "money_tracker_sg" {
  name        = "money-tracker-sg"
  description = "Allow SSH and HTTP"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "money_tracker" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.money_tracker_sg.id]

  tags = {
    Name = "money-tracker"
  }
}

output "public_ip" {
  value = aws_instance.money_tracker.public_ip
}
```

### 2. Apply Terraform
```bash
cd terraform
terraform init
terraform plan
terraform apply -auto-approve
```
Note the output `public_ip`.

---

## Configuration Management (Ansible)

### 1. Inventory (`ansible/inventory.ini`)
```ini
[money-tracker]
ec2-instance ansible_host=<EC2_PUBLIC_IP> ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/devops-key.pem
```

### 2. Playbook (`ansible/playbook.yml`)
```yaml
---
- name: Configure Money Tracker server
  hosts: money-tracker
  become: yes
  vars:
    docker_image: "your-dockerhub-username/money-tracker:latest"
    container_name: "money-tracker"
    nginx_conf_src: "../nginx/default.conf"
    nginx_conf_dest: "/etc/nginx/sites-available/default"

  tasks:
    - name: Update apt cache
      apt:
        update_cache: yes

    - name: Install Docker
      apt:
        name: docker.io
        state: present

    - name: Install NGINX
      apt:
        name: nginx
        state: present

    - name: Start Docker service
      systemd:
        name: docker
        state: started
        enabled: yes

    - name: Create web root directory
      file:
        path: /var/www/html
        state: directory

    - name: Copy frontend files
      copy:
        src: "../frontend/"
        dest: "/var/www/html/"
        owner: www-data
        group: www-data
        mode: '0644'

    - name: Pull Docker image
      docker_image:
        name: "{{ docker_image }}"
        source: pull

    - name: Run Docker container
      docker_container:
        name: "{{ container_name }}"
        image: "{{ docker_image }}"
        state: started
        restart_policy: always
        ports:
          - "5000:5000"
        env:
          FLASK_ENV: "production"

    - name: Copy NGINX configuration
      copy:
        src: "{{ nginx_conf_src }}"
        dest: "{{ nginx_conf_dest }}"
        owner: root
        group: root
        mode: '0644'
      notify: restart nginx

    - name: Enable NGINX site
      file:
        src: "{{ nginx_conf_dest }}"
        dest: "/etc/nginx/sites-enabled/default"
        state: link

    - name: Remove default site
      file:
        path: "/etc/nginx/sites-enabled/default"
        state: absent
      ignore_errors: yes

  handlers:
    - name: restart nginx
      systemd:
        name: nginx
        state: restarted
```

### 3. NGINX configuration (`nginx/default.conf`)
```nginx
server {
    listen 80;
    server_name _;

    location / {
        root /var/www/html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 4. Run Ansible
```bash
cd ansible
ansible-playbook -i inventory.ini playbook.yml
```

---

## Deployment Walkthrough
1. Develop and test locally.
2. Build multi‑arch Docker image and push to Docker Hub.
3. Provision EC2 instance using Terraform.
4. Run Ansible to install dependencies, pull image, and configure NGINX.
5. Access the application via the EC2 public IP.

---

## Screenshots

Take the following screenshots for documentation:

1. **Local Development**
<img width="724" height="28" alt="Screenshot 2026-03-29 at 12 01 51 PM" src="https://github.com/user-attachments/assets/57072769-7ecc-4bee-9af5-1620203445ce" />

   - `curl http://localhost:5001/api/transactions` output showing `[]`
   - Browser showing the Money Tracker UI with a transaction added

3. **Docker Build**  

<img width="399" height="200" alt="Screenshot 2026-03-29 at 12 10 10 PM" src="https://github.com/user-attachments/assets/ffd3f5c3-fc79-47bf-aff1-0d3923adb45f" />

   - Terminal showing successful `docker buildx build` command with multi‑arch output

5. **Terraform Apply**  
<img width="779" height="879" alt="Screenshot 2026-03-29 at 12 02 51 PM" src="https://github.com/user-attachments/assets/497fb5e4-59d4-46bd-974b-58fe74d1e408" />


   - `terraform apply` output showing the EC2 instance creation and public IP

7. **Ansible Playbook Run**  
<img width="924" height="860" alt="Screenshot 2026-03-29 at 12 03 21 PM" src="https://github.com/user-attachments/assets/339f2929-6203-41c6-a708-64e545fd909d" />


   - Terminal showing successful playbook execution (green tasks, changed count)

9. **Final Application**  
<img width="798" height="377" alt="Screenshot 2026-03-29 at 12 03 55 PM" src="https://github.com/user-attachments/assets/13147c3b-6e30-435e-8625-df5bf83cb067" />

    - Browser at `http://<EC2-IP>` displaying the Money Tracker UI
   - Adding a transaction and seeing it appear in the list


10. **NGINX Status**  
  <img width="843" height="298" alt="Screenshot 2026-03-29 at 12 04 47 PM" src="https://github.com/user-attachments/assets/1b5191a4-a786-4d07-acd4-b4c3ec3c2920" />

   - `sudo systemctl status nginx` showing active (running)

---

## Troubleshooting & Common Issues

### 1. Python virtual environment and package installation
**Issue:** `error: externally-managed-environment` when installing Flask on macOS.  
**Resolution:** Create and activate a virtual environment before `pip install`.

### 2. Flask fails to start with `pkgutil.get_loader` error
**Issue:** Flask 2.3.2 incompatible with Python 3.14.  
**Resolution:** Upgrade Flask to ≥3.0.0 in `requirements.txt`.

### 3. Port 5000 already in use on macOS
**Issue:** AirPlay Receiver uses port 5000.  
**Resolution:** Run Flask on a different port (e.g., 5001) by changing `app.run(port=5001)`.

### 4. EC2 instance creation fails with `InvalidAMIID.NotFound`
**Issue:** Placeholder AMI ID not valid.  
**Resolution:** Query the correct Ubuntu 22.04 AMI for your region using AWS CLI and update `variables.tf`.

### 5. SSH permission denied after recreating key pair
**Issue:** New key pair created but instance still has old public key.  
**Resolution:** Destroy the instance and re‑apply Terraform to associate the new key.

### 6. Docker pull fails with `no matching manifest for linux/amd64`
**Issue:** Image built only for ARM64 (Mac) cannot run on x86_64 EC2.  
**Resolution:** Build a multi‑arch image using `docker buildx` with `--platform linux/amd64,linux/arm64`.

### 7. NGINX not listening on port 80 despite service running
**Issue:** The configuration file was not linked to `sites-enabled`.  
**Resolution:** Manually create symlink:  
```bash
sudo ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default
sudo systemctl reload nginx
```

### 8. Connection refused on port 80 (curl)
**Issue:** Security group missing inbound rule for port 80.  
**Resolution:** Add rule with `aws ec2 authorize-security-group-ingress` or re‑run Terraform.

### 9. Ansible YAML syntax errors
**Issue:** Indentation errors in playbook.  
**Resolution:** Use consistent 2‑space indentation and place `vars` block at same level as `hosts` and `become`.

### 10. Docker permission denied on EC2
**Issue:** User not in `docker` group.  
**Resolution:** `sudo usermod -aG docker $USER` and log out/in.

---

## Clean Up
To avoid AWS charges, destroy resources when not needed:
```bash
cd terraform
terraform destroy -auto-approve
```

---

## Next Steps
- **CI/CD** with GitHub Actions: build, push, and deploy on every push.
- **Persistent storage** using PostgreSQL (AWS RDS).
- **Custom domain** and HTTPS (Let's Encrypt).
- **Monitoring** with Prometheus/Grafana or AWS CloudWatch.

---

## Conclusion
This project demonstrates a complete DevOps workflow: from local development to automated deployment on AWS using modern tools. The Money Tracker app serves as a simple but realistic example of how to build and deploy a full‑stack application with infrastructure as code, configuration management, and containerization.

---

**Happy DevOps!** 🚀
