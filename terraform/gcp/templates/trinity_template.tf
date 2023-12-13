provider "google" {
  project = "GCP_PROJECT_ID"
  credentials = file("credentials.json")
  region  = "asia-east1"
  zone    = "asia-east1-b"
}

resource "google_compute_instance" "my_instance" {
  count = 3 # Create three crystaldb new nodes
  name = "crys-ha-node-${count.index}"
  machine_type = "GCP_MACHINE_TYPE"
  zone = "asia-east1-b"
  allow_stopping_for_update = true
  tags = ["http-server", "https-server"]

  boot_disk {
    initialize_params {
      image = "rocky-linux-cloud/rocky-linux-8"
    }
  }
  

  network_interface {
    network = "default"
    access_config {
      //necessary even if it is empty
    }
  }
}



# Print the output (both external and internal ips)
output "instance_external_ips" {
  description = "External IPs of instances"
  value       = google_compute_instance.my_instance.*.network_interface.0.access_config.0.nat_ip
}

output "instance_internal_ips" {
  description = "Internal IPs of instances"
  value       = google_compute_instance.my_instance.*.network_interface.0.network_ip
}
