data "http" "my_ip" {
  url = "https://checkip.amazonaws.com"
}

locals {
  # Se resuelve en cada plan/apply contra tu IP pública actual — ya no hay que
  # actualizar manualmente ninguna variable cuando el ISP la cambie.
  my_cidr = ["${chomp(data.http.my_ip.response_body)}/32"]
}