# ==========================================
# BUILD STAGE
# ==========================================

FROM node:22-alpine AS builder

WORKDIR /app

# Copy package files first for Docker cache
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application source
COPY . .

# Build SvelteKit application
RUN npm run build


# ==========================================
# PRODUCTION STAGE
# ==========================================

FROM node:22-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=3000

# Copy the built SvelteKit application
COPY --from=builder /app/build ./build

# Copy package files
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/package-lock.json ./package-lock.json

# Keep the installed dependencies from the builder.
# This is safer for the current package.json because
# SvelteKit and adapter-node are in devDependencies.
COPY --from=builder /app/node_modules ./node_modules

# Expose SvelteKit port
EXPOSE 3000

# Start SvelteKit
CMD ["node", "build"]