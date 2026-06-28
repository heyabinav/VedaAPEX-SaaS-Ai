import { Router } from "express";

import { analyticsController } from "../../controllers/analytics.controller";

export const analyticsRouter = Router();

analyticsRouter.get("/leaderboard", analyticsController.leaderboard);
