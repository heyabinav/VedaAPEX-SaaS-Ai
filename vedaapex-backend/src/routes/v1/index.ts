import { Router } from "express";

import { adminRouter } from "./admin.routes";
import { aiRouter } from "./ai.routes";
import { analyticsRouter } from "./analytics.routes";
import { authRouter } from "./auth.routes";
import { mediaRouter } from "./media.routes";
import { paymentRouter } from "./payment.routes";
import { notificationRouter } from "./notification.routes";
import { paperRouter } from "./paper.routes";
import { studyRouter } from "./study.routes";

export const apiV1Router = Router();

apiV1Router.use("/auth", authRouter);
apiV1Router.use("/papers", paperRouter);
apiV1Router.use("/ai", aiRouter);
apiV1Router.use("/study", studyRouter);
apiV1Router.use("/admin", adminRouter);
apiV1Router.use("/analytics", analyticsRouter);
apiV1Router.use("/media", mediaRouter);
apiV1Router.use("/payments", paymentRouter);
apiV1Router.use("/notifications", notificationRouter);
