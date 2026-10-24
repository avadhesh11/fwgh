# Multi-stage Production Dockerfile for Wind Forecast Decision Portal — React Frontend

# Stage 1: Build production bundle
FROM node:22-alpine AS builder

WORKDIR /app

# Install dependencies first for optimal Docker layer caching
COPY package.json package-lock.json ./
RUN npm ci

# Pass configurable API URL at build time; defaults to relative '/api' (proxied by Nginx)
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Copy source code and configuration files
COPY tsconfig*.json vite.config.ts index.html ./
COPY public ./public
COPY src ./src

# Compile TypeScript and build production bundle
RUN npm run build

# Stage 2: Serve static files with Nginx
FROM nginx:alpine

# Remove default nginx html files
RUN rm -rf /usr/share/nginx/html/*

# Copy build artifacts from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose HTTP port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://127.0.0.1/healthz || exit 1

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
