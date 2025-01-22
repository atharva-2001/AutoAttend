# Use an official Node runtime as the base image
FROM node:18-alpine

# Set the working directory in the container
WORKDIR /app

# Copy package.json and package-lock.json (if available)
COPY package*.json ./

# Install dependencies
RUN npm config set legacy-peer-deps true
RUN npm ci

# Copy the rest of the frontend source code
COPY . .

# Set the API URL for production
ENV NEXT_PUBLIC_API_URL=https://auto.lightmind.in
ENV NEXT_PUBLIC_WS_URL=wss://auto.lightmind.in

# Build the application
RUN npm run build

# Expose the port the app runs on
EXPOSE 3000

# Command to run the application in production mode
CMD ["npm", "start"]
