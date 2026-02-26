```bash
python3.11 -m venv venv
```

```bash
source venv/bin/activate
```

```bash
pip install -r requirements.txt
```

```python
python -m uvicorn app.main:app --reload
```