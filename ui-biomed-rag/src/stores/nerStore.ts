import { create } from "zustand";

interface Entity {
  text: string;
  start?: number;
  end?: number;
  confidence?: number;
  label?: string;
  assertion_status?: string;
}

interface NerResult {
  entities: Record<string, Entity[]>;
  provider?: string;
  error?: string;
  custom_labels?: string[];
  assertion_enabled?: boolean;
  relations?: [string, string, string][];
}

interface NerState {
  text: string;
  selectedTypes: string[];
  customLabels: string;
  enableAssertion: boolean;
  provider: string;
  result: NerResult | null;
  fileName: string | null;
  fileError: string | null;
  progress: { current: number; total: number } | null;
  viewMode: "entities" | "relgraph";
  showAllRelations: boolean;

  setText: (v: string) => void;
  setSelectedTypes: (v: string[] | ((prev: string[]) => string[])) => void;
  setCustomLabels: (v: string) => void;
  setEnableAssertion: (v: boolean) => void;
  setProvider: (v: string) => void;
  setResult: (v: NerResult | null) => void;
  setFileName: (v: string | null) => void;
  setFileError: (v: string | null) => void;
  setProgress: (v: { current: number; total: number } | null) => void;
  setViewMode: (v: "entities" | "relgraph") => void;
  setShowAllRelations: (v: boolean) => void;
}

const ALL_ENTITY_TYPES = [
  "DISEASE", "DRUG", "GENE", "PROTEIN", "ANATOMY", "CHEMICAL", "ONCOLOGY",
];

export const useNerStore = create<NerState>((set) => ({
  text: "",
  selectedTypes: [...ALL_ENTITY_TYPES],
  customLabels: "",
  enableAssertion: false,
  provider: "gliner",
  result: null,
  fileName: null,
  fileError: null,
  progress: null,
  viewMode: "entities",
  showAllRelations: false,

  setText: (v) => set({ text: v }),
  setSelectedTypes: (v) =>
    set((state) => ({
      selectedTypes: typeof v === "function" ? v(state.selectedTypes) : v,
    })),
  setCustomLabels: (v) => set({ customLabels: v }),
  setEnableAssertion: (v) => set({ enableAssertion: v }),
  setProvider: (v) => set({ provider: v }),
  setResult: (v) => set({ result: v }),
  setFileName: (v) => set({ fileName: v }),
  setFileError: (v) => set({ fileError: v }),
  setProgress: (v) => set({ progress: v }),
  setViewMode: (v) => set({ viewMode: v }),
  setShowAllRelations: (v) => set({ showAllRelations: v }),
}));
