# Build stage
FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source files
COPY src ./src
COPY public ./public

# Build the app
RUN npm run build

# Production stage
FROM nginx:alpine

# Remove default nginx config
RUN rm -rf /etc/nginx/conf.d
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built app from builder stage
COPY --from=builder /app/build /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]