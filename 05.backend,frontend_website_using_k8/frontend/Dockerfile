FROM nginx:alpine
RUN rm -rf /etc/nginx/conf.d
COPY index.html /usr/share/nginx/html/index.html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80