import { startMediaProcessingWorker } from "./media-processing.queue";
import { startNotificationWorker } from "./notification.queue";
import { startPaperProcessingWorker } from "./paper-processing.queue";

export const startQueueWorkers = async () => {
  await Promise.all([startPaperProcessingWorker(), startNotificationWorker(), startMediaProcessingWorker()]);
};
