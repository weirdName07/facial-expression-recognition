# Stage 1: Build the Angular application
FROM node:20 AS build-step
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build -- --configuration production

# Stage 2: Serve the application with Nginx
FROM nginx:alpine
# Copy build output to Nginx HTML directory
COPY --from=build-step /app/dist/frontend /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Default Nginx configuration is usually sufficient, but can be customized here
CMD ["nginx", "-g", "daemon off;"]
