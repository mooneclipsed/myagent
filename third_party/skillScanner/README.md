# SkillScanner

Standalone static security scanner for agent skill packages, extracted from QwenPaw's skill scanner core.

## Install

```bash
python -m pip install -e .
```

For tests:

```bash
python -m pip install -e '.[dev]'
```

## Python API

```python
from skillscanner import SkillScanner

result = SkillScanner().scan_skill("/path/to/skill")
print(result.is_safe)
print(result.to_dict())
```

With a custom policy:

```python
from skillscanner import ScanPolicy, SkillScanner

policy = ScanPolicy.from_yaml("my_policy.yaml")
result = SkillScanner(policy=policy).scan_skill("/path/to/skill")
```

## CLI

```bash
skillscanner /path/to/skill
skillscanner /path/to/skill --policy my_policy.yaml
skillscanner /path/to/skill --compact
```

The CLI prints JSON and exits with:

- `0` when the skill has no CRITICAL/HIGH findings
- `1` when the skill is unsafe
- `2` for argument/runtime errors
