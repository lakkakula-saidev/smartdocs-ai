# Fix Plan for LangChain Import Issues

## Problem Analysis

The current code in `main.py` has import issues because:

1. **Missing Dependencies**: The `requirements.txt` only includes the core `langchain` package
2. **Outdated Import Paths**: LangChain has been modularized into separate packages

## Current Problematic Imports

### Lines 85-86 (Primary Issues)
```python
from langchain_openai import OpenAIEmbeddings        # Missing: langchain-openai
from langchain_community.vectorstores import Chroma  # Missing: langchain-chroma
```

### Line 151 (Additional Issue)
```python
from langchain_openai import ChatOpenAI              # Missing: langchain-openai
```

## Required Fixes

### 1. Update requirements.txt
Add the missing LangChain packages:
```
fastapi
uvicorn
python-multipart
langchain
langchain-openai
langchain-chroma
openai
pypdf
tiktoken
```

### 2. Fix Import Statements
Update the import on line 86:
```python
# OLD:
from langchain_community.vectorstores import Chroma

# NEW:
from langchain_chroma import Chroma
```

All other imports (`langchain_openai.OpenAIEmbeddings`, `langchain_openai.ChatOpenAI`) are correct once the package is installed.

## Package Dependencies Mapping

| Component | Old Location | New Package | New Import |
|-----------|-------------|-------------|------------|
| `OpenAIEmbeddings` | `langchain_openai` | `langchain-openai` | `from langchain_openai import OpenAIEmbeddings` |
| `ChatOpenAI` | `langchain_openai` | `langchain-openai` | `from langchain_openai import ChatOpenAI` |
| `Chroma` | `langchain_community.vectorstores` | `langchain-chroma` | `from langchain_chroma import Chroma` |
| `RecursiveCharacterTextSplitter` | `langchain.text_splitter` | `langchain` | No change needed |
| `RetrievalQA` | `langchain.chains` | `langchain` | No change needed |

## Implementation Steps

1. Update `requirements.txt` to include `langchain-openai` and `langchain-chroma`
2. Change the Chroma import from `langchain_community.vectorstores` to `langchain_chroma`
3. Verify all imports resolve correctly
4. Test the application functionality

## Additional Considerations

- The `chromadb` package in requirements.txt might be redundant as `langchain-chroma` should include it
- Consider version pinning for production deployments
- The current imports use lazy loading which is good for performance

## Files to Modify

1. `requirements.txt` - Add missing packages
2. `main.py:86` - Fix Chroma import path