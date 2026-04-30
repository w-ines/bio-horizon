/**
 * Form to create a new PubMed corpus ingestion job
 */

"use client";

import { useState } from "react";
import { JobCreateRequest } from "./types";
import { jobsApi } from "./api";

interface CreateJobFormProps {
  onJobCreated?: (jobId: string) => void;
  onCancel?: () => void;
}

export function CreateJobForm({ onJobCreated, onCancel }: CreateJobFormProps) {
  const [formData, setFormData] = useState<JobCreateRequest>({
    query: "",
    mindate: "",
    maxdate: "",
    batch_size: 500,
    max_batches: undefined,
    processing_mode: "metadata_only",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const result = await jobsApi.createJob(formData);
      onJobCreated?.(result.job_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create job");
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 p-6 border rounded-lg bg-white">
      <h2 className="text-2xl font-bold">Create Ingestion Job</h2>

      {/* Query */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          PubMed Query *
        </label>
        <input
          type="text"
          required
          value={formData.query}
          onChange={(e) => setFormData({ ...formData, query: e.target.value })}
          placeholder="e.g., diabetes mellitus treatment"
          className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <p className="text-xs text-gray-500 mt-1">
          Use PubMed search syntax. This will fetch ALL matching articles.
        </p>
      </div>

      {/* Date Range */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Min Date
          </label>
          <input
            type="text"
            value={formData.mindate}
            onChange={(e) => setFormData({ ...formData, mindate: e.target.value })}
            placeholder="YYYY or YYYY/MM or YYYY/MM/DD"
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Max Date
          </label>
          <input
            type="text"
            value={formData.maxdate}
            onChange={(e) => setFormData({ ...formData, maxdate: e.target.value })}
            placeholder="YYYY or YYYY/MM or YYYY/MM/DD"
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Processing Mode */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Processing Mode
        </label>
        <div className="grid grid-cols-3 gap-3">
          <button
            type="button"
            onClick={() => setFormData({ ...formData, processing_mode: "metadata_only" })}
            className={`p-3 border-2 rounded-lg text-left transition-all ${
              formData.processing_mode === "metadata_only"
                ? "border-green-500 bg-green-50"
                : "border-gray-200 hover:border-gray-300"
            }`}
          >
            <div className="font-medium text-sm">⚡ Fast</div>
            <div className="text-xs text-gray-500 mt-1">Metadata only</div>
            <div className="text-xs text-green-600 mt-1">~2-5 min</div>
          </button>
          <button
            type="button"
            onClick={() => setFormData({ ...formData, processing_mode: "deferred_ner" })}
            className={`p-3 border-2 rounded-lg text-left transition-all ${
              formData.processing_mode === "deferred_ner"
                ? "border-yellow-500 bg-yellow-50"
                : "border-gray-200 hover:border-gray-300"
            }`}
          >
            <div className="font-medium text-sm">📦 Deferred</div>
            <div className="text-xs text-gray-500 mt-1">Metadata now, NER later</div>
            <div className="text-xs text-yellow-600 mt-1">~2-5 min + NER</div>
          </button>
          <button
            type="button"
            onClick={() => setFormData({ ...formData, processing_mode: "full" })}
            className={`p-3 border-2 rounded-lg text-left transition-all ${
              formData.processing_mode === "full"
                ? "border-blue-500 bg-blue-50"
                : "border-gray-200 hover:border-gray-300"
            }`}
          >
            <div className="font-medium text-sm">🧬 Full</div>
            <div className="text-xs text-gray-500 mt-1">NER + Knowledge Graph</div>
            <div className="text-xs text-blue-600 mt-1">~10-30 min</div>
          </button>
        </div>
      </div>

      {/* Advanced Options */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Batch Size
          </label>
          <input
            type="number"
            min="10"
            max="500"
            value={formData.batch_size}
            onChange={(e) => setFormData({ ...formData, batch_size: parseInt(e.target.value) })}
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-500 mt-1">Articles per batch (10-500)</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Max Batches (optional)
          </label>
          <input
            type="number"
            min="1"
            value={formData.max_batches || ""}
            onChange={(e) => setFormData({ ...formData, max_batches: e.target.value ? parseInt(e.target.value) : undefined })}
            placeholder="Unlimited"
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-500 mt-1">Leave empty for full corpus</p>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">❌ {error}</p>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <button
          type="submit"
          disabled={loading || !formData.query}
          className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          {loading ? "Creating Job..." : "Create Job"}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg font-medium hover:bg-gray-300 disabled:bg-gray-100"
          >
            Cancel
          </button>
        )}
      </div>

      {/* Info */}
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-800">
          <strong>ℹ️ Note:</strong> This will create an asynchronous job that:
        </p>
        <ul className="text-sm text-blue-700 mt-2 ml-4 space-y-1 list-disc">
          <li>Searches PubMed using the History Server</li>
          <li>Fetches articles in batches of {formData.batch_size}</li>
          {formData.processing_mode === "full" && (
            <>
              <li>Extracts medical entities (NER)</li>
              <li>Ingests into the Knowledge Graph</li>
            </>
          )}
          {formData.processing_mode === "metadata_only" && (
            <li>Stores article metadata (title, abstract, authors, MeSH terms)</li>
          )}
          {formData.processing_mode === "deferred_ner" && (
            <>
              <li>Stores article metadata first (fast)</li>
              <li>NER + KG processing can be triggered later</li>
            </>
          )}
          <li>Can be resumed if it fails</li>
        </ul>
      </div>
    </form>
  );
}
