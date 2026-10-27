import { request } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type DailyQuestion = components["schemas"]["DailyQuestion"];
export type Exploration = components["schemas"]["ExplorationState"];
export type Answer = components["schemas"]["ExplorationAnswer"];
export type Job = components["schemas"]["RecommendationJob"];
export const getDaily = () => request<DailyQuestion>("/questions/daily", "GET");
export const createExploration = (version: string) => request<Exploration>("/explorations", "POST", { question_version_id: version });
export const getExploration = (id: string) => request<Exploration>(`/explorations/${id}`, "GET");
export const submitAnswer = (id: string, answer: Answer) => request<Exploration>(`/explorations/${id}/answers`, "POST", answer);
export const recommend = (id: string, key: string) => request<Job>("/recommendations", "POST", { reading_intent_id: id, limit: 3 }, key);
export const getJob = (id: string) => request<Job>(`/recommendations/${id}`, "GET");
