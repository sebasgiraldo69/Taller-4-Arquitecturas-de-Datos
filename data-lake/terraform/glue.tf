resource "aws_glue_catalog_database" "datalake" {
  name        = "taller4_datalake"
  description = "Data Lake de noticias de El Tiempo - Silver y Gold"
}
