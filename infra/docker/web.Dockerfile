FROM node:20-alpine

WORKDIR /app

COPY package.json /app/package.json
COPY frontend /app/frontend

WORKDIR /app/frontend

RUN npm install

EXPOSE 3000

CMD ["npm", "run", "dev"]