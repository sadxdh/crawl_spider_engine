FROM node:20-slim

WORKDIR /app

COPY package.json .
RUN npm install --registry=https://registry.npmmirror.com

COPY server.js .

EXPOSE 3000

CMD ["node", "server.js"]
