import swaggerJsdoc from "swagger-jsdoc";

import { env } from "./env";

export const swaggerSpec = swaggerJsdoc({
  definition: {
    openapi: "3.0.3",
    info: {
      title: `${env.APP_NAME} API`,
      version: "1.0.0",
      description: "Backend APIs for papers, authentication, AI evaluation, study plans, and analytics.",
    },
    servers: [
      {
        url: `${env.APP_BASE_URL}${env.API_PREFIX}/${env.API_VERSION}`,
      },
    ],
    components: {
      securitySchemes: {
        bearerAuth: {
          type: "http",
          scheme: "bearer",
          bearerFormat: "JWT",
        },
      },
    },
  },
  apis: ["./src/routes/**/*.ts", "./src/controllers/**/*.ts"],
});
