# Running Tests

From the repository root:

```bash
uv run pytest                                      # run the suite
uv run --python 3.9 pytest                         # against another Python version
uv run coverage run -m pytest && uv run coverage html
```

`test_master_output.svg` is the golden file `test_all` compares against.
