FROM nginx:alpine

# Install curl for health checks
RUN apk add --no-cache curl

# Remove default nginx configs - BOTH files needed
RUN rm /etc/nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Copy custom nginx configuration  
COPY nginx.conf /etc/nginx/nginx.conf

# Create directory for static files
RUN mkdir -p /usr/share/nginx/html/static && \
    mkdir -p /usr/share/nginx/html/media && \
    chown -R nginx:nginx /usr/share/nginx/html

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/nginx-status/ || exit 1

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]