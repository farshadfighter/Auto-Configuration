FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

# docker-compose.yml bind-mounts ./frontend over /app but keeps /app/node_modules as its own
# anonymous volume (so the host's node_modules, or lack thereof, doesn't shadow the image's).
# That volume survives `docker compose up --build`, so a rebuild after adding a new npm
# dependency still starts the container with the OLD node_modules and Vite fails to resolve
# the new import. Running `npm install` on every start (fast no-op when the lockfile already
# matches) keeps that volume in sync instead of only installing once at image build time.
CMD ["sh", "-c", "npm install && npm run dev -- --host 0.0.0.0"]
