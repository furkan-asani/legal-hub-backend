# Reranker Configuration Guide

The Legal Hub RAG system includes support for reranking search results to improve relevance and accuracy. This guide covers setup and configuration.

## Overview

Reranking is a post-processing step that takes the initial vector search results and reorders them based on semantic relevance to the query. This typically improves the quality of retrieved documents.

## Supported Rerankers

### Cohere Rerank (Recommended)

- **Provider**: `cohere`
- **Model**: Uses Cohere's rerank-english-v2.0 model
- **Accuracy**: High quality semantic reranking
- **Cost**: Pay-per-use API calls

## Environment Configuration

Add these variables to your `.env` file:

```bash
# Reranker Settings
RERANKER_ENABLED=true
RERANKER_PROVIDER=cohere
RERANKER_TOP_N=3

# Cohere API Key (required for Cohere reranking)
COHERE_API_KEY=your_cohere_api_key_here
```

### Configuration Options

| Variable            | Default  | Description                           |
| ------------------- | -------- | ------------------------------------- |
| `RERANKER_ENABLED`  | `true`   | Enable/disable reranking              |
| `RERANKER_PROVIDER` | `cohere` | Reranker provider (`cohere`, `none`)  |
| `RERANKER_TOP_N`    | `3`      | Number of top results after reranking |
| `COHERE_API_KEY`    | -        | Cohere API key (required for Cohere)  |

## Setup Instructions

### 1. Install Dependencies

```bash
pip install llama-index-postprocessor-cohere-rerank
```

### 2. Get Cohere API Key

1. Sign up at [Cohere Dashboard](https://dashboard.cohere.ai/)
2. Navigate to API Keys section
3. Create a new API key
4. Add it to your `.env` file as `COHERE_API_KEY`

### 3. Configure Environment

Update your `.env` file with the reranker settings shown above.

### 4. Test Configuration

Run the test suite to verify reranker setup:

```bash
python test_query_system.py
```

Look for the "Reranker Functionality" test section.

## Usage Examples

### Basic Usage

The reranker is automatically used when enabled:

```python
from rag.rag_engine import RAGEngine

# Initialize RAG engine (reranker auto-configured)
rag = RAGEngine()

# Query with automatic reranking
result = rag.query("What are the payment terms?")
print(f"Reranker used: {result['reranker_used']}")
```

### Compare With/Without Reranking

```python
# Compare results with and without reranking
comparison = rag.compare_with_and_without_reranker(
    "What are the liability limits in the contract?"
)

print("With reranker:", comparison['with_reranker']['citations'][0]['text'])
print("Without reranker:", comparison['without_reranker']['citations'][0]['text'])
```

### Disable Reranking Temporarily

```python
# Query without reranking
result = rag.query_without_reranker("What are the termination clauses?")
```

## API Integration

The `/query` endpoint automatically uses reranking when enabled:

```bash
curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What are the payment terms?",
       "case_id": 1
     }'
```

Response includes reranker information:

```json
{
  "answer": "Based on the contract...",
  "citations": [
    {
      "source": "contract.pdf",
      "text": "Payment terms: 30 days net...",
      "score": 0.95,
      "reranked": true
    }
  ],
  "reranker_used": "cohere",
  "reranker_top_n": 3
}
```

## Performance Impact

### Benefits

- **Improved Relevance**: Better semantic matching
- **Higher Accuracy**: More relevant chunks retrieved
- **Better User Experience**: More accurate answers

### Considerations

- **API Latency**: Additional ~200-500ms per query
- **API Costs**: Per-query charges from Cohere
- **Rate Limits**: Subject to Cohere API limits

## Troubleshooting

### Common Issues

**1. "Reranker not available" Warning**

```
Solution: Check COHERE_API_KEY is set and valid
```

**2. "Import Error" for Cohere Rerank**

```
Solution: pip install llama-index-postprocessor-cohere-rerank
```

**3. Reranker Not Improving Results**

```
Check: Ensure you have diverse, relevant documents indexed
Verify: Query is specific enough for reranking to help
```

### Debug Mode

Enable debug logging to see reranker behavior:

```python
import logging
logging.getLogger("llama_index.postprocessor.cohere_rerank").setLevel(logging.DEBUG)
```

## Alternative Configurations

### Disable Reranking

```bash
RERANKER_ENABLED=false
# or
RERANKER_PROVIDER=none
```

### Adjust Reranking Aggressiveness

```bash
# Get more results before reranking (better quality, slower)
RERANKER_TOP_N=5

# Get fewer results (faster, potentially lower quality)
RERANKER_TOP_N=2
```

## Cost Optimization

- **Caching**: Results are not cached by default
- **Selective Use**: Consider disabling for simple queries
- **Batch Processing**: Rerank multiple queries together when possible
- **Monitoring**: Track API usage in Cohere dashboard

## Next Steps

1. Test reranking with your specific documents
2. Compare answer quality with/without reranking
3. Monitor API usage and costs
4. Adjust `RERANKER_TOP_N` based on your needs
5. Consider implementing result caching for frequently asked questions
