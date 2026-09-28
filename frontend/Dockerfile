# ---------- 构建阶段 ----------
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# 构建期注入前端环境变量
ARG VITE_AMAP_WEB_JS_KEY=""
ARG VITE_API_BASE_URL=""
ENV VITE_AMAP_WEB_JS_KEY=$VITE_AMAP_WEB_JS_KEY \
    VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build:only

# ---------- 运行阶段 ----------
FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
