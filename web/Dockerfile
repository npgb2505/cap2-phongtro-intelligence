FROM node:22-alpine

WORKDIR /app

COPY package.json package.json
COPY package-lock.json package-lock.json
COPY tsconfig.json tsconfig.json
COPY next.config.mjs next.config.mjs
COPY next-env.d.ts next-env.d.ts
COPY app /app/app
COPY components /app/components
COPY lib /app/lib

RUN npm ci
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0"]
