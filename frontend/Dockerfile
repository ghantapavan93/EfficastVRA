FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY . .
RUN npm run build

FROM node:20-alpine AS run
WORKDIR /app
ENV NODE_ENV=production
ENV BACKEND_URL=http://backend:8000
COPY --from=build /app ./
EXPOSE 3000
CMD ["npm", "run", "start"]
