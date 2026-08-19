# Next 16 requires Node >= 20.9; node:22-slim is the current LTS line.
FROM node:22-slim AS deps
WORKDIR /app
# Copy the lockfile too so `npm ci` can install the exact resolved tree.
# `npm ci` (not `npm install`) keeps image builds reproducible and fails
# loudly if package.json and the lockfile have drifted apart.
COPY package.json package-lock.json* ./
RUN npm ci

FROM node:22-slim AS runner
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
# .dockerignore excludes the host node_modules/.next, so this cannot
# clobber the Linux dependency tree installed above.
COPY . .
ENV NODE_ENV=development
EXPOSE 3000
CMD ["npm", "run", "dev"]
