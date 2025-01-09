# Getting Started with Biomapper

## Installation

Biomapper can be installed via pip:

```pip install biomapper```

## Basic Usage

Here's a quick example of mapping a metabolite name:

```python
from biomapper.mapping import MetaboliteNameMapper

# Initialize the mapper
mapper = MetaboliteNameMapper()

# Map a metabolite name
result = mapper.map_name("glucose")
print(result.standardized_name)