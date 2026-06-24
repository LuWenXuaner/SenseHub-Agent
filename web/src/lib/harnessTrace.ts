export type HarnessTracePass = {
  role: string;
  model: string;
  summary: string;
  [key: string]: unknown;
};

export type HarnessTrace = {
  strategy: string;
  complexity_score: number;
  model_used?: string;
  passes: HarnessTracePass[];
};
