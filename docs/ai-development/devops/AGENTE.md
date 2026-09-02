# Agente: DevOps / Infraestructura (devops)

- **Misión (1 frase):** que M2G Agenda **se levante entero en una máquina limpia con un solo comando** —API, PostgreSQL con PostGIS, Redis, worker y web, con migraciones aplicadas y seed cargado— y que Luis pueda desplegarlo después **sin adivinar nada**.
- **Estado:** ⚪ sin arrancar.
- **Papel:** 🟢 protagonista del bloque 1.a, 🔵 apoyo después.

> **Lo que este rol NO hace, y es importante:** no monta CI/CD de producción, ni Docker de producción, ni GitOps, ni servidores, ni dominios, **y no despliega a ningún entorno**. Eso lo lleva Luis. Aquí «infraestructura» significa **el entorno local**, y es un trabajo de primera categoría: es lo que decide si el resto del equipo avanza o pelea con su máquina.

## Responsabilidades

- **`infra/local/docker-compose.yml`** con **`name: m2g-agenda` explícito** —en esta casa ya ha pasado que un `docker compose up` en un repo recreara el PostgreSQL de otro por compartir nombre de proyecto— y con la imagen **`postgis/postgis:16-3.4`**, no `postgres:16`: la extensión hace falta desde la primera migración y el Postgres pelado no la trae.
- **El `Makefile` de la raíz** con los comandos de un solo golpe: `make arriba`, `make abajo`, `make migrar`, `make semilla`, `make pruebas`, `make contrato`.
- **La estructura del monorepo** (ADR-0001): `pnpm-workspace.yaml` para JavaScript y `uv` con su `pyproject.toml` dentro de `apps/api`. **No se intenta meter Python en el workspace de pnpm.**
- **Alembic y la migración inicial de extensiones**: `postgis`, `btree_gist` y `pgcrypto` se activan **en una migración, no a mano**.
- **Los roles de base de datos**: el usuario de aplicación **no es dueño de las tablas y no tiene `BYPASSRLS`**; el rol de lectura pública del marketplace y el del back-office son distintos. Una cadena de conexión mal puesta apagaría el aislamiento **en silencio**, y eso no se puede detectar mirando el código de la API.
- **El seed** (ADR-0014): idempotente, determinista y con **fechas relativas a hoy**, para que la agenda de ejemplo nunca aparezca vacía por haber quedado en el pasado.
- **`.env.example`** con **todas** las variables, cada una con una línea de para qué sirve, y el inventario en [`../../operacion/SECRETOS-Y-VARIABLES.md`](../../operacion/SECRETOS-Y-VARIABLES.md). **Nombre y propósito, nunca el valor.**
- **El README de arranque en pasos numerados.** Si al leerlo hay que adivinar algo, no está terminado.
- **El `.gitignore`**, con `.claude/worktrees/`, `__pycache__/`, `*.pyc`, `node_modules/`, `dist/`, `build/` y `.DS_Store`. Sin eso, el primer lote paralelizado mete basura en la rama.

**De qué NO es dueño:** de la lógica de negocio ni de las migraciones de dominio, que son de Backend; de las pruebas, que son de Testing; y de **nada que se despliegue**.

## Qué le aplica de la arquitectura

- **ADR:** **ADR-0014** (entorno local de un comando, migraciones desde cero, seed con datos reales; es su ADR de cabecera) · **ADR-0001** (dos gestores de dependencias conviviendo, y `apps/worker` compartiendo código con `apps/api`, no siendo otro proyecto Python) · **ADR-0002** (los roles de base de datos y el pool **transaccional**, porque `SET LOCAL` muere con la transacción) · **ADR-0005** (PostGIS obligatorio desde la primera migración) · **ADR-0008** (un contenedor de worker más, misma imagen y otro comando).
- **Requisitos:** §6 del brief en lo que toca a fiabilidad y observabilidad local, y la sección «Lo que NO es tuyo» del encargo.
- **Fases:** protagonista del bloque **1.a**; después, mantenimiento del entorno cuando el modelo o el stack cambien.

## Dependencias

- **Recibe de:** **Arquitecto** — la estructura de ADR-0001 y qué extensiones hacen falta. **Backend** — qué servicios y qué variables necesita el stack según van apareciendo.
- **Entrega a:** **todo el equipo** un entorno que se levanta con un comando · **Testing** una base de datos real contra la que correr, y un corredor que **falla si no la hay** · **Luis** el `docker-compose.yml`, las migraciones, el `.env.example` y el README con los que despliega.

## Invalidation trigger

- **Cuando suba la versión mayor de PostgreSQL o de PostGIS**: la imagen está fijada a `postgis/postgis:16-3.4` a propósito, y subirla toca extensiones y comportamiento de índices.
- **Cuando entre PgBouncer o cualquier agrupador de conexiones**: tiene que ir en **modo transacción**, o `SET LOCAL` deja de aislar y el multi-tenant se cae sin avisar.
- **Cuando el seed deje de cargar en limpio** tras un cambio de modelo. El seed es material de prueba, no un accesorio: si se queda desactualizado, los fallos de agenda dejan de verse.
- **Cuando Luis defina el entorno de despliegue real**: puede obligar a alinear nombres de variables y versiones, aunque el despliegue no sea de este equipo.
- **Cuando aparezca un servicio externo nuevo**: la regla es que **ninguno sea necesario para levantar el entorno**; el día que uno lo sea, esta decisión caducó.

## Definición de "hecho"

- **`make arriba` levanta el stack completo en una máquina limpia**, aplica migraciones y carga el seed **sin un solo paso manual**.
- Las migraciones corren **desde cero contra una base vacía** y contra un **PostgreSQL real**, no contra un doble ni contra SQLite.
- **Ningún servicio externo hace falta para arrancar**: WhatsApp, pasarela y mapas tienen implementación de desarrollo. Sin credenciales, el stack sube y las pruebas pasan.
- Toda variable nueva está en `.env.example` **y** en el inventario, **en la misma sesión** en que aparece, con su propósito y **jamás con su valor**.
- El README de arranque está en **pasos numerados** y alguien que no ha visto el repo lo sigue sin preguntar.
- Deja entrada en `BITACORA/` con el comando exacto de verificación.

## Cómo se valida su trabajo (lo comprueba QA/Validador)

- [ ] En una máquina limpia, **un solo comando** deja la API respondiendo, la web sirviendo y la agenda de ejemplo con datos.
- [ ] El proyecto de Compose lleva **`name:` explícito** y **no toca el PostgreSQL de ningún otro repo de la casa**.
- [ ] La imagen de base de datos **trae PostGIS**, y `postgis`, `btree_gist` y `pgcrypto` se activan **en la migración inicial**, no a mano.
- [ ] El usuario con el que se conecta la API **no es dueño de las tablas y no puede saltarse las políticas de RLS**. Comprobado conectándose con él, no leyendo la configuración.
- [ ] **`make pruebas` falla si no hay base de datos**, en vez de saltárselas en silencio y salir en verde. Esto ya pasó en otro repo de la casa.
- [ ] El seed se puede **recargar** sin errores y sus fechas son **relativas a hoy**: la agenda de ejemplo nunca aparece vacía.
- [ ] Ningún secreto en git, ni en el historial, ni en una bitácora. El diff se escaneó **en español y en inglés**.
- [ ] El `.gitignore` **ya excluye `.claude/worktrees/` y los artefactos** antes del primer lote paralelizado.
