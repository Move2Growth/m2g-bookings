-- Roles de la base local. Se ejecuta una sola vez, al crear el volumen.
--
-- El aislamiento entre negocios (ADR-0002) depende de que el usuario de la aplicación
-- NO sea dueño de las tablas y NO tenga BYPASSRLS: el dueño de una tabla se salta sus
-- propias políticas de seguridad por fila, así que si la API se conectara como
-- `agenda_owner` el RLS no protegería absolutamente nada.
--
-- Son cuatro roles y cada uno existe por un motivo distinto (§1.8 del modelo de datos).

-- La API en modo negocio. Sujeta a RLS: ni un SELECT sin WHERE se lleva datos ajenos.
CREATE ROLE agenda_api LOGIN PASSWORD 'agenda' NOBYPASSRLS;

-- El marketplace y las páginas públicas. Solo lectura y solo sobre lo publicable:
-- nunca ve reservas ni fichas de cliente.
CREATE ROLE agenda_publico LOGIN PASSWORD 'agenda' NOBYPASSRLS;

-- El back-office de M2G. Acceso amplio y auditado, con su propia sesión y 2FA.
-- Nunca es el mismo rol que la API pública: si lo fuera, un fallo en un endpoint público
-- tendría los permisos del equipo interno.
CREATE ROLE agenda_admin LOGIN PASSWORD 'agenda' NOBYPASSRLS;

GRANT CONNECT ON DATABASE agenda TO agenda_api, agenda_publico, agenda_admin;
GRANT USAGE ON SCHEMA public TO agenda_api, agenda_publico, agenda_admin;

-- Los permisos sobre las tablas se conceden en la migración, que es quien las crea.
-- Aquí solo se fija el valor por defecto para lo que venga después, de modo que una tabla
-- nueva no nazca inaccesible para la aplicación.
ALTER DEFAULT PRIVILEGES FOR ROLE agenda_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO agenda_api;
ALTER DEFAULT PRIVILEGES FOR ROLE agenda_owner IN SCHEMA public
  GRANT SELECT ON TABLES TO agenda_publico;
ALTER DEFAULT PRIVILEGES FOR ROLE agenda_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO agenda_admin;
ALTER DEFAULT PRIVILEGES FOR ROLE agenda_owner IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO agenda_api, agenda_admin;
