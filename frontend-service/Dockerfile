# ---- Build Stage ----
# Use an official Node.js runtime as the base image for building
# Choose a specific LTS version (e.g., 18) and Alpine for smaller size
FROM node:18-alpine AS builder

# Set the working directory in the container
WORKDIR /app

# Copy package.json and package-lock.json (or yarn.lock)
# This leverages Docker cache - dependencies are only reinstalled if these files change
COPY package.json ./
COPY package-lock.json ./
# If using yarn, uncomment the next line and comment out the previous one
# COPY yarn.lock ./

# Install dependencies using npm ci for faster, reliable builds from lock file
RUN npm ci
# If using yarn, uncomment the next line and comment out the previous one
# RUN yarn install --frozen-lockfile

# Copy the rest of the application source code
COPY . .

# Build the React application for production
# This creates an optimized static build in the 'build' folder
RUN npm run build

# ---- Runtime Stage ----
# Use a lightweight Nginx image to serve the static files
FROM nginx:stable-alpine

# Copy the custom Nginx configuration file
# This configures Nginx to work correctly with React Router (Single Page Application)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the static build output from the 'builder' stage to Nginx's web root directory
COPY --from=builder /app/build /usr/share/nginx/html

# Expose port 80 (the default port Nginx listens on)
EXPOSE 80

# The default Nginx command runs Nginx in the foreground, which is suitable for Docker
# CMD ["nginx", "-g", "daemon off;"] (This is the default CMD for the nginx image, so not strictly needed to specify)

