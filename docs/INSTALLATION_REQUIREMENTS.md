# Installation Requirements

**Text-to-SQL Multi-Agent System — Installation Only**

This document covers system and Python environment setup only. No schema, application code, or runtime configuration is included.

---

## A. System-Level Installations

### A.1 Python Version Verification

Requirement: **Python 3.10 or higher**.

**Check installed version:**

```bash
python --version
```

If missing or older than 3.10, install from [python.org](https://www.python.org/downloads/) and ensure **"Add Python to PATH"** is checked (Windows).

### A.2 pip Upgrade

Use a current pip to avoid dependency resolution issues:

```bash
python -m pip install --upgrade pip
```

---

## B. Python Dependency Installation

Use a **virtual environment** (create and activate it before installing).

### B.1 Install from requirements.txt

From the project root (with venv activated):

```bash
pip install -r requirements.txt
```

### B.2 Package Roles and Notes

| Package | Purpose | Notes |
|--------|---------|--------|
| **fastapi** | Web API framework | Core application server. |
| **uvicorn** | ASGI server | Runs FastAPI in production and development. |
| **pydantic** | Data validation | Used by FastAPI for request/response models; required explicitly for type-safe config and helpers. |
| **python-dotenv** | Environment variables | Loads `.env` for secrets and config. |
| **faiss-cpu** | Vector similarity search (CPU) | Used for embeddings/retrieval without GPU. |

### B.3 Compatibility

- **Windows:** All listed packages provide wheels; `faiss-cpu` works without extra system libraries.
- **macOS:** Same; on Apple Silicon use ARM-compatible wheels (provided by the packages above).
- **Python:** Keep to **3.10+** as specified; 3.11 or 3.12 are supported by this stack.

---

## C. FAISS Installation Notes

### C.1 CPU-Only Installation

Use the CPU-only package (no CUDA):

```bash
pip install faiss-cpu
```

Do **not** install `faiss` or `faiss-gpu` unless you intend to use a GPU and have the correct CUDA stack.

### C.2 Common Issues

- **ImportError or link errors:** Uninstall any existing `faiss` or `faiss-gpu`, then install only `faiss-cpu`.
- **Wrong platform:** Ensure `faiss-cpu` is installed in the same environment and Python version you use to run the app.
- **Slow install:** First install can take a minute while the wheel is downloaded and unpacked.

### C.3 Verify FAISS

```bash
python -c "import faiss; print(f'FAISS {faiss.__version__} OK')"
```

No error and a version string means FAISS is usable.

---

## E. Verification Checklist

Run these in order with the virtual environment activated:

| Step | Command | Expected |
|------|---------|----------|
| 1. Python | `python --version` | `Python 3.10.x` or higher |
| 2. pip | `pip --version` | Version and path inside your venv |
| 3. FastAPI | `python -c "import fastapi; print('FastAPI OK')"` | `FastAPI OK` |
| 4. Uvicorn | `python -c "import uvicorn; print('Uvicorn OK')"` | `Uvicorn OK` |
| 5. Pydantic | `python -c "import pydantic; print('Pydantic OK')"` | `Pydantic OK` |
| 6. dotenv | `python -c "import dotenv; print('dotenv OK')"` | `dotenv OK` |
| 7. FAISS | `python -c "import faiss; print('FAISS OK')"` | `FAISS OK` |

If every step prints OK, the installation is complete.

---

## Sequential Command List

Run in order (venv already created and activated):

```bash
# 1. Confirm Python 3.10+
python --version

# 2. Upgrade pip
python -m pip install --upgrade pip

# 3. Install all Python dependencies
pip install -r requirements.txt

# 4. Verify stack
python -c "import fastapi; import uvicorn; import pydantic; import dotenv; import faiss; print('All packages OK')"
```

---

*Document scope: installation only. No database schema, application code, or deployment steps.*
