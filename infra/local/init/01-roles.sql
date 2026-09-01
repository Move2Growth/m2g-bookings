-- Roles de la base local. Se ejecuta una sola vez, al crear el volumen.
--
-- El aislamiento entre negocios (ADR-0002) depende de que el usuario de la aplicación
-- NO sea dueño de las tablas y NO tenga BYPASSRLS: el dueño de una tabla se salta sus
-- propias políticas de seguridad por fila, así que si la API se conectara como
-- `agenda_owner` el RLS no protegería absolutamente nada.

-- Usuario de la API y del worker: sin BYPASSRLS, sin ser dueño de nada.
CREATE ROLE agenda_app LOGIN PASSWORD 'agenda' NOBYPASSRLS;

-- Usuario de solo lectura para las consultas públicas del marketplace, que cruzan
-- todos los negocios y por tanto no pueden ir con el tenant fijado.
CREATE ROLE agenda_publico LOGIN PASSWORD 'agenda' NOBYPASSRLS;

GRANT CONNECT ON DATABASE agenda TO agenda_app, agenda_publico;
GRANT USAGE ON SCHEMA public TO agenda_app, agenda_publico;

-- Los permisos sobre las tablas se conceden en la migración inicial, que es quien las crea.
-- Aquí solo se fija el valor por defecto para lo que venga después, de modo que una tabla
-- nueva no nazca inaccesible para la aplicación.
ALTER DEFAULT PRIVILEGES FOR ROLE agenda_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO agenda_app;
ALTER DEFAULT PRIVILEGES FOR ROLE agenda_owner IN SCHEMA public
  GRANT SELECT ON TABLES TO agenda_publico;
ALTER DEFAULT PRIVILEGES FOR ROLE agenda_owner IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO agenda_app;
