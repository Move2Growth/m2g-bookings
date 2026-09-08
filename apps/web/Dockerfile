# La web en local, dentro de Docker como el resto del entorno.
#
# Va en Docker por una razón concreta que ya se cobró una demo: corriendo `next start` a mano en
# el puerto 3100, otro proyecto del mismo portátil se había quedado con el puerto y servía **su**
# build. Resultado: la portada cargaba y todo lo demás daba 404 sin un solo error en el log.
# Un contenedor con su propio puerto publicado no puede confundirse de proyecto.
FROM node:22-alpine

WORKDIR /repo
RUN corepack enable

# Las dependencias se instalan desde la raíz del monorepo: la web depende de `@agenda/tokens`,
# que es un paquete del propio espacio de trabajo.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY packages ./packages
COPY apps/web/package.json ./apps/web/package.json
RUN pnpm install --frozen-lockfile

COPY packages ./packages
COPY apps/web ./apps/web

WORKDIR /repo/apps/web
EXPOSE 3100
CMD ["sh", "-c", "pnpm build && pnpm exec next start --port 3100 --hostname 0.0.0.0"]
