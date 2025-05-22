# Use a tiny nginx image to serve static files
FROM nginx:alpine

# Remove default site
RUN rm /usr/share/nginx/html/*

# Copy our index.html
COPY index.html /usr/share/nginx/html/index.html

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
