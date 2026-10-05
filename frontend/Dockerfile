FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy application source
COPY . .

# Expose Metro bundler and web ports
EXPOSE 8081 19000 19006

# Start Expo in web mode
CMD ["npx", "expo", "start", "--web", "--port", "19006"]
