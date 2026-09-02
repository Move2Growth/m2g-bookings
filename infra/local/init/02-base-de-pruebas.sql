-- Una base aparte para las pruebas.
--
-- Las pruebas de concurrencia y de aislamiento **tienen que confirmar transacciones** —una
-- carrera entre dos transacciones no se puede simular deshaciendo al final—, así que dejan
-- filas escritas. Si compartieran base con el desarrollo, los negocios inventados de las
-- pruebas aparecerían en el listado del marketplace junto a los del seed, y a la tercera
-- ejecución nadie sabría qué está mirando.
--
-- Los roles son del clúster, no de la base, así que agenda_api, agenda_publico y agenda_admin
-- valen aquí igual. Los permisos sobre las tablas los concede la migración, que corre en las
-- dos bases por separado.
CREATE DATABASE agenda_pruebas OWNER agenda_owner;

GRANT CONNECT ON DATABASE agenda_pruebas TO agenda_api, agenda_publico, agenda_admin;
