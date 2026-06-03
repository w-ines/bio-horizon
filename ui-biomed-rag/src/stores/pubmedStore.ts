import { create } from "zustand";

interface Article {
  pmid: string;
  title: string;
  abstract: string;
  journal: string;
  pub_date: string;
  authors: string[];
  mesh_terms: string[];
}

interface SearchResult {
  total: number;
  pmids: string[];
  articles: Article[];
  error?: string;
}

interface PubMedState {
  query: string;
  maxResults: number;
  mindate: string;
  maxdate: string;
  selectedPubTypes: string[];
  journalsInput: string;
  language: string;
  selectedSpecies: string[];
  result: SearchResult | null;
  expandedPmid: string | null;

  setQuery: (v: string) => void;
  setMaxResults: (v: number) => void;
  setMindate: (v: string) => void;
  setMaxdate: (v: string) => void;
  setSelectedPubTypes: (v: string[] | ((prev: string[]) => string[])) => void;
  setJournalsInput: (v: string) => void;
  setLanguage: (v: string) => void;
  setSelectedSpecies: (v: string[] | ((prev: string[]) => string[])) => void;
  setResult: (v: SearchResult | null) => void;
  setExpandedPmid: (v: string | null) => void;
}

export const usePubMedStore = create<PubMedState>((set) => ({
  query: "",
  maxResults: 10,
  mindate: "",
  maxdate: "",
  selectedPubTypes: [],
  journalsInput: "",
  language: "",
  selectedSpecies: [],
  result: null,
  expandedPmid: null,

  setQuery: (v) => set({ query: v }),
  setMaxResults: (v) => set({ maxResults: v }),
  setMindate: (v) => set({ mindate: v }),
  setMaxdate: (v) => set({ maxdate: v }),
  setSelectedPubTypes: (v) =>
    set((state) => ({
      selectedPubTypes: typeof v === "function" ? v(state.selectedPubTypes) : v,
    })),
  setJournalsInput: (v) => set({ journalsInput: v }),
  setLanguage: (v) => set({ language: v }),
  setSelectedSpecies: (v) =>
    set((state) => ({
      selectedSpecies: typeof v === "function" ? v(state.selectedSpecies) : v,
    })),
  setResult: (v) => set({ result: v }),
  setExpandedPmid: (v) => set({ expandedPmid: v }),
}));
