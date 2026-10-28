import type { QuickstartOutput } from "@/types/api";

export type QuickstartSavedState = {
  answers: Record<string, string>;
  result: QuickstartOutput | null;
  activeGroup: "ethics" | "tipsc" | "dfv";
};

const emptyState = (): QuickstartSavedState => ({ answers: {}, result: null, activeGroup: "ethics" });
const storageKey = (userId: string) => `agis:quickstart:v1:${userId}`;

export function loadQuickstartState(userId: string | null | undefined): QuickstartSavedState {
  if (!userId) return emptyState();
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey(userId)) || "null");
    if (!saved || typeof saved !== "object") return emptyState();
    const answers = saved.answers && typeof saved.answers === "object"
      ? Object.fromEntries(Object.entries(saved.answers).filter((entry): entry is [string, string] => typeof entry[1] === "string"))
      : {};
    const activeGroup = ["ethics", "tipsc", "dfv"].includes(saved.activeGroup) ? saved.activeGroup : "ethics";
    const result = saved.result && Array.isArray(saved.result.parameters) ? saved.result as QuickstartOutput : null;
    return { answers, result, activeGroup };
  } catch {
    return emptyState();
  }
}

export function saveQuickstartState(userId: string, state: QuickstartSavedState): void {
  try {
    localStorage.setItem(storageKey(userId), JSON.stringify(state));
  } catch {
    // The form still works when browser storage is unavailable or full.
  }
}

export function clearQuickstartState(userId: string): void {
  try {
    localStorage.removeItem(storageKey(userId));
  } catch {
    // The in-memory form can still be reset when browser storage is unavailable.
  }
}
