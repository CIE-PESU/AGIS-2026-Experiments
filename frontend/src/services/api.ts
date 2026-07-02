import {
  mockComplianceResult,
  mockDFVResult,
  mockFollowUps,
  mockJTBDResult,
  mockTIPSAfterRound1,
  mockTIPSFinal,
  mockTIPSInitial
} from "@/data/mockData";

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export async function checkCompliance() {
  await wait(2500);
  return mockComplianceResult;
}

export async function getInitialTIPSScores() {
  await wait(3000);
  return { result: mockTIPSInitial, followUp: mockFollowUps[0] };
}

export async function submitFollowUp(round: number, _answer: string) {
  await wait(2500);
  if (round === 0) return { result: mockTIPSAfterRound1, followUp: mockFollowUps[1] };
  return { result: mockTIPSFinal, followUp: null };
}

export async function runDFVAnalysis() {
  await wait(4000);
  return mockDFVResult;
}

export async function generateJTBD() {
  await wait(3000);
  return mockJTBDResult;
}
