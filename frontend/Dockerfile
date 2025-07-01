# Stage 1: Build the React application
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of the application source code
COPY . .

# Build the production-ready static files
RUN npm run build


# Stage 2: Serve the static files with a minimal server
FROM node:20-alpine

WORKDIR /app

# Install `serve`, a simple static file server
RUN npm install -g serve

# Copy the built static files from the builder stage
COPY --from=builder /app/dist ./dist

# Expose the port the server will run on
EXPOSE 3000

# The command to start the server
# It serves the `dist` folder and listens on all interfaces on port 3000
CMD ["serve", "-s", "dist", "-l", "3000"] 