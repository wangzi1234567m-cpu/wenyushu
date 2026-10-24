import { bootstrapSession } from "@/lib/api/client";

type State = "idle" | "loading" | "ready" | "error";
let state: State = "idle";
let pending: Promise<void> | undefined;
const listeners = new Set<() => void>();
const publish = (next: State) => { state = next; listeners.forEach((listener) => listener()); };

export const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
};
export const snapshot = () => state;
export const serverSnapshot = (): State => "idle";
export function initializeSession(): Promise<void> {
  if (state === "ready") return Promise.resolve();
  if (pending) return pending;
  publish("loading");
  pending = bootstrapSession().then(() => publish("ready")).catch(() => publish("error"))
    .finally(() => { pending = undefined; });
  return pending;
}
