# OpenMed Integration Guide

## Overview

OpenMed is now fully integrated into the BioHorizon NER system, providing state-of-the-art biomedical entity extraction with three key capabilities:

- **F2a**: Standard NER (DISEASE, DRUG, GENE, PROTEIN, ANATOMY, CHEMICAL, ONCOLOGY)
- **F2b**: Zero-shot NER with custom labels (BRAIN_REGION, BIOMARKER, etc.)
- **F2c**: Assertion Status (PRESENT, NEGATED, HYPOTHETICAL, HISTORICAL)

## Installation

```bash
# Install OpenMed with Hugging Face support
pip install 'openmed[hf]>=0.6.3'

# Or install from requirements.txt
pip install -r requirements.txt
```

## Architecture

```
ner/
├── backends/
│   ├── openmed_backend.py       # F2a: Standard NER
│   ├── openmed_zeroshot.py      # F2b: Zero-shot custom labels
│   └── gliner_backend.py        # Fallback (uses assertion module)
├── assertion.py                 # F2c: Assertion Status detection
├── router.py                    # Routes to appropriate backend
└── schemas.py                   # NerEntity, NerResult dataclasses
```

## Usage

### 1. Standard NER (F2a)

Extract standard biomedical entities:

```python
from ner.router import extract_from_text

result = extract_from_text(
    "Patient started on imatinib for chronic myeloid leukemia.",
    entity_types=["DISEASE", "DRUG"],
    provider="openmed"
)

# result.entities["DISEASE"] → ["chronic myeloid leukemia"]
# result.entities["DRUG"] → ["imatinib"]
```

### 2. Zero-shot NER (F2b)

Extract custom entity types without retraining:

```python
result = extract_from_text(
    "The hippocampus shows elevated tau and amyloid-beta levels.",
    custom_labels=["BRAIN_REGION", "BIOMARKER"],
    provider="openmed"
)

# result.entities["BRAIN_REGION"] → ["hippocampus"]
# result.entities["BIOMARKER"] → ["tau", "amyloid-beta"]
```

### 3. Assertion Status (F2c)

Qualify entities with contextual status:

```python
result = extract_from_text(
    "Patient has no hypertension. Further trials may confirm efficacy.",
    entity_types=["DISEASE"],
    enable_assertion=True,
    provider="openmed"
)

# result.entities["DISEASE"][0].text → "hypertension"
# result.entities["DISEASE"][0].assertion_status → "NEGATED"
```

## API Endpoint

The NER API endpoint supports all three features:

```bash
curl -X POST http://localhost:8000/ner/extract \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Semaglutide shows neuroprotective effects in Alzheimer disease.",
    "entity_types": ["DRUG", "DISEASE"],
    "enable_assertion": true,
    "provider": "openmed"
  }'
```

Response:
```json
{
  "entities": {
    "DRUG": [
      {
        "text": "Semaglutide",
        "confidence": 0.95,
        "assertion_status": "PRESENT",
        "label": "DRUG"
      }
    ],
    "DISEASE": [
      {
        "text": "Alzheimer disease",
        "confidence": 0.92,
        "assertion_status": "PRESENT",
        "label": "DISEASE"
      }
    ]
  },
  "provider": "openmed",
  "assertion_enabled": true
}
```

## OpenMed Models

### Standard NER Models (F2a)

| Entity Type | Model Name | Description |
|-------------|-----------|-------------|
| DISEASE | `disease_detection_superclinical` | Diseases, pathologies |
| DRUG | `pharma_detection_superclinical` | Medications, molecules |
| GENE | `gene_detection_genecorpus` | Genes |
| PROTEIN | `protein_detection_bc5cdr` | Proteins |
| ANATOMY | `anatomy_detection_electramed` | Organs, structures |
| CHEMICAL | `chemical_detection_bc5cdr` | Chemical compounds |
| ONCOLOGY | `disease_detection_superclinical` | Cancer-related entities |

### Zero-shot Model (F2b)

- **GLiNER**: `gliner_medium` - Supports arbitrary custom labels

### Assertion Model (F2c)

- **Assertion**: `assertion_detection_superclinical` - Detects PRESENT/NEGATED/HYPOTHETICAL/HISTORICAL

## Configuration

### Environment Variables

```bash
# OpenMed Standard NER
OPENMED_CONFIDENCE_THRESHOLD=0.7
OPENMED_GROUP_ENTITIES=true
OPENMED_USE_MEDICAL_TOKENIZER=true

# OpenMed Assertion
OPENMED_ENABLE_ASSERTION=false
OPENMED_ASSERTION_MODEL=assertion_detection_superclinical

# OpenMed Zero-shot
OPENMED_ZEROSHOT_THRESHOLD=0.5
OPENMED_GLINER_MODEL=gliner_medium

# Provider selection (openmed or gliner)
NER_PROVIDER=openmed

# Override specific models
OPENMED_MODEL_DISEASE=disease_detection_superclinical
OPENMED_MODEL_DRUG=pharma_detection_superclinical
```

## Frontend Integration

The frontend NER page (`ui-med-rag/src/app/ner/page.tsx`) fully supports:

1. **Standard entity types** with all 7 types from spec
2. **Custom labels input** for zero-shot NER
3. **Assertion status toggle** with visual badges (P/N/H/H)

## Fallback Strategy

If OpenMed is not installed, the system gracefully falls back:

1. **Standard NER**: Falls back to GLiNER2
2. **Zero-shot NER**: Falls back to GLiNER2
3. **Assertion Status**: Falls back to heuristic-based detection

## Performance

- **Standard NER**: ~100-200ms per abstract (CPU)
- **Zero-shot NER**: ~150-300ms per abstract (CPU)
- **Assertion Status**: +50-100ms overhead per entity
- **Batch processing**: Supported for efficiency

## Troubleshooting

### OpenMed not found

```bash
pip install 'openmed[hf]'
```

### Model download issues

OpenMed models are downloaded from Hugging Face on first use. Ensure internet connectivity.

### Assertion not working

Check that `enable_assertion=True` is set and OpenMed is installed. The system will fall back to heuristics if the model is unavailable.

## Next Steps

1. **Test OpenMed installation**: `python -c "from openmed import analyze_text; print('OK')"`
2. **Run NER extraction**: Use the API endpoint or frontend
3. **Monitor performance**: Check logs for model loading times
4. **Tune thresholds**: Adjust confidence thresholds via env vars

## References

- OpenMed Docs: https://openmed.life/docs/
- OpenMed GitHub: https://github.com/maziyarpanahi/openmed
- Project Spec: `PROJECT_SPECIFICATION.md` (F2a, F2b, F2c)
