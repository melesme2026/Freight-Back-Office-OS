FROM node:20-alpine AS deps

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

FROM node:20-alpine AS builder

WORKDIR /app

ARG NEXT_PUBLIC_API_BASE_URL=""
ARG NEXT_PUBLIC_API_VERSION_PREFIX="/api/v1"

ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
ENV NEXT_PUBLIC_API_VERSION_PREFIX=${NEXT_PUBLIC_API_VERSION_PREFIX}

COPY --from=deps /app/node_modules /app/node_modules
COPY frontend /app

RUN npm run build

FROM node:20-alpine AS runner

ENV NODE_ENV=production

WORKDIR /app

COPY --from=builder /app /app

EXPOSE 3000

CMD ["npm", "run", "start"]
